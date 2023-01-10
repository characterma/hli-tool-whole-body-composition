import torch
import torch.nn as nn
import numpy as np
import torch.nn.functional as F
from torch import cat
from loguru import logger
from torch.utils.data import Dataset
from scipy.ndimage import zoom
from tensorflow.keras.utils import to_categorical
import os, time, sys
from torch.cuda.amp import autocast, GradScaler
from collections import OrderedDict


def passthrough(x, **kwargs):
    return x


def ELUCons(elu, nchan):
    if elu:
        return nn.ELU(inplace=True)
    else:
        return nn.PReLU(nchan)


class LUConv(nn.Module):
    def __init__(self, nchan, elu):
        super(LUConv, self).__init__()
        self.relu1 = ELUCons(elu, nchan)
        self.conv1 = nn.Conv3d(nchan, nchan, kernel_size=5, padding=2)

        self.bn1 = torch.nn.BatchNorm3d(nchan)

    def forward(self, x):
        out = self.relu1(self.bn1(self.conv1(x)))
        return out


def _make_nConv(nchan, depth, elu):
    layers = []
    for _ in range(depth):
        layers.append(LUConv(nchan, elu))
    return nn.Sequential(*layers)


class InputTransition(nn.Module):
    def __init__(self, in_channels, elu):
        super(InputTransition, self).__init__()
        self.num_features = 16
        self.in_channels = in_channels

        self.conv1 = nn.Conv3d(self.in_channels, self.num_features, kernel_size=5, padding=2)

        self.bn1 = torch.nn.BatchNorm3d(self.num_features)

        self.relu1 = ELUCons(elu, self.num_features)

    def forward(self, x):
        out = self.conv1(x)
        repeat_rate = int(self.num_features / self.in_channels)
        out = self.bn1(out)
        x16 = x.repeat(1, repeat_rate, 1, 1, 1)
        return self.relu1(torch.add(out, x16))


class DownTransition(nn.Module):
    def __init__(self, inChans, nConvs, elu, dropout=False):
        super(DownTransition, self).__init__()
        outChans = 2 * inChans
        self.down_conv = nn.Conv3d(inChans, outChans, kernel_size=2, stride=2)
        self.bn1 = torch.nn.BatchNorm3d(outChans)

        self.do1 = passthrough
        self.relu1 = ELUCons(elu, outChans)
        self.relu2 = ELUCons(elu, outChans)
        if dropout:
            self.do1 = nn.Dropout3d()
        self.ops = _make_nConv(outChans, nConvs, elu)

    def forward(self, x):
        down = self.relu1(self.bn1(self.down_conv(x)))
        out = self.do1(down)
        out = self.ops(out)
        out = self.relu2(torch.add(out, down))
        return out


class UpTransition(nn.Module):
    def __init__(self, inChans, outChans, nConvs, elu, dropout=False):
        super(UpTransition, self).__init__()
        self.up_conv = nn.ConvTranspose3d(inChans, outChans // 2, kernel_size=2, stride=2)

        self.bn1 = torch.nn.BatchNorm3d(outChans // 2)
        self.do1 = passthrough
        self.do2 = nn.Dropout3d()
        self.relu1 = ELUCons(elu, outChans // 2)
        self.relu2 = ELUCons(elu, outChans)
        if dropout:
            self.do1 = nn.Dropout3d()
        self.ops = _make_nConv(outChans, nConvs, elu)

    def forward(self, x, skipx):
        out = self.do1(x)
        skipxdo = self.do2(skipx)
        out = self.relu1(self.bn1(self.up_conv(out)))
        xcat = torch.cat((out, skipxdo), 1)
        out = self.ops(xcat)
        out = self.relu2(torch.add(out, xcat))
        return out


class OutputTransition(nn.Module):
    def __init__(self, in_channels, classes, elu):
        super(OutputTransition, self).__init__()
        self.classes = classes
        self.conv1 = nn.Conv3d(in_channels, classes, kernel_size=5, padding=2)
        self.bn1 = torch.nn.BatchNorm3d(classes)

        self.conv2 = nn.Conv3d(classes, classes, kernel_size=1)
        self.relu1 = ELUCons(elu, classes)

    def forward(self, x):
        # convolve 32 down to channels as the desired classes
        out = self.relu1(self.bn1(self.conv1(x)))
        out = self.conv2(out)
        return out

class UpTransitionNoConv(nn.Module):
    def __init__(self, inChans, outChans, nConvs, elu, dropout=False):
        # inChans=62, outChans=32, nConvs=1, elu=True
        super(UpTransitionNoConv, self).__init__()
        self.up_conv = nn.ConvTranspose3d(inChans, outChans // 2, kernel_size=2, stride=2)

        self.bn1 = torch.nn.BatchNorm3d(outChans // 2)
        self.do1 = passthrough
        self.do2 = nn.Dropout3d()
        self.relu1 = ELUCons(elu, outChans // 2)
        if dropout:
            self.do1 = nn.Dropout3d()
        

    def forward(self, x, skipx):
        out = self.do1(x)
        skipxdo = self.do2(skipx)
        out = self.relu1(self.bn1(self.up_conv(out)))
        xcat = torch.cat((out, skipxdo), 1)
        return xcat

class VNet_Parallelism(nn.Module):
    """
    Implementations based on the Vnet paper: https://arxiv.org/abs/1606.04797
    """

    def __init__(self, elu=True, in_channels=1, classes=1):
        super(VNet_Parallelism, self).__init__()
        self.classes = classes
        self.in_channels = in_channels
        logger.info("begin initialize model struction")
        self.in_tr = InputTransition(in_channels, elu=elu)
        self.down_tr32 = DownTransition(16, 1, elu)
        self.down_tr64 = DownTransition(32, 2, elu)
        self.down_tr128 = DownTransition(64, 3, elu, dropout=False)
        self.down_tr256 = DownTransition(128, 2, elu, dropout=False)
        self.up_tr256 = UpTransition(256, 256, 2, elu, dropout=False)       
        self.up_tr128 = UpTransition(256, 128, 2, elu, dropout=False)
        self.up_tr64 = UpTransition(128, 64, 1, elu)
        # 版本1
        # self.up_tr32 = UpTransition(64, 32, 1, elu)
        
        # 版本2
        self.up_tr32 = UpTransitionNoConv(64, 32, 1, elu)
        self.up_tr32_ops = _make_nConv(32, 1, elu)
        self.up_tr32_relu2 = ELUCons(elu, 32)

        
        self.out_tr = OutputTransition(32, classes, elu)



    def forward(self, x):
        out16 = self.in_tr(x)
        logger.debug(f"out16: {out16.shape}")
        out32 = self.down_tr32(out16)
        logger.debug(f"out32: {out32.shape}")
        out64 = self.down_tr64(out32)
        # print(f"out64: {out64.shape}, self.down_tr128: {next(self.down_tr128.parameters()).device}")
        out128 = self.down_tr128(out64)
        logger.debug(f"out128: {out128.shape}")
        out256 = self.down_tr256(out128)
        logger.debug(f"out256: {out256.shape}, out128: {out128.shape}")
        out = self.up_tr256(out256, out128)
        logger.debug(f"out: {out.shape}， out64: {out64.shape}")
        out = self.up_tr128(out, out64)
        logger.debug(f"out: {out.shape}, out32: {out32.shape}")
        out = self.up_tr64(out, out32)
        logger.debug(f"out: {out.shape}, out16: {out16.shape}")
        # 版本1
        # out = self.up_tr32(out, out16)

        # 版本2
        out_uptr32 = self.up_tr32(out, out16)
        out_uptr32_ops_val = self.up_tr32_ops(out_uptr32)
        out = self.up_tr32_relu2(torch.add(out_uptr32_ops_val, out_uptr32))

        logger.debug(f"out: {out.shape}")
        out = self.out_tr(out)
        logger.debug(f"out: {out.shape}")
        return out
