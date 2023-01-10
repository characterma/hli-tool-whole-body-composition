from loguru import logger
from tensorflow.keras import Model
from tensorflow.keras import backend as K
from tensorflow.keras.backend import concatenate
from tensorflow.keras.layers import Concatenate
from tensorflow.keras.layers import Conv3DTranspose as Deconvolution3D
from tensorflow.keras.layers import Input, Dropout, Conv3D, MaxPooling3D, BatchNormalization, Conv3DTranspose, \
    Activation
from tensorflow.keras.models import Sequential


def get_model(input_shape, num_classes=3):
    logger.info(f"begin loading model weight, input shape: {input_shape}, num classes: {num_classes}")
    x = Input(input_shape)

    # Min-Max normalization
    #   normalized = Lambda(lambda x: x / 255) (x)

    normalized = x

    conv1 = Conv3D(32, (3,3,3), activation='relu', padding='same')(normalized)
    batch1 = BatchNormalization(axis=-1)(conv1)
    # batch1 = Dropout(0.2)(batch1)
    conv2 = Conv3D(64, (3,3,3), activation='relu', padding='same')(batch1)
    batch2 = BatchNormalization(axis=-1)(conv2)
    max1  = MaxPooling3D(pool_size=(2,2,2), strides=2)(batch2)

    conv3 = Conv3D(64,  (3,3,3), activation='relu', padding='same') (max1)
    batch3 = BatchNormalization(axis=-1)(conv3)
    # batch3 = Dropout(0.2)(batch3)
    conv4 = Conv3D(128, (3,3,3), activation='relu', padding='same') (batch3)
    batch4 = BatchNormalization(axis=-1)(conv4)
    max2  = MaxPooling3D(pool_size=(2,2,2), strides=2) (batch4)

    conv5 = Conv3D(128, (3,3,3), activation='relu', padding='same') (max2)
    batch5 = BatchNormalization(axis=-1)(conv5)
    # batch5 = Dropout(0.2)(batch5)
    conv6 = Conv3D(256, (3,3,3), activation='relu', padding='same') (batch5)
    batch6 = BatchNormalization(axis=-1)(conv6)
    max3  = MaxPooling3D(pool_size=(2,2,2), strides=2) (batch6)

    conv7 = Conv3D(256, (3,3,3), activation='relu', padding='same') (max3)
    batch7 = BatchNormalization(axis=-1)(conv7)
    # batch7 = Dropout(0.2)(batch7)
    conv8 = Conv3D(512, (3,3,3), activation='relu', padding='same') (batch7)
    batch8 = BatchNormalization(axis=-1)(conv8)
    up1  = Conv3DTranspose(512, kernel_size=(2,2,2), strides=2) (batch8)

    concat1 = concatenate([up1, conv6])
    conv9 = Conv3D(256, (3,3,3), activation='relu', padding='same') (concat1)
    batch9 = BatchNormalization(axis=-1)(conv9)
    # batch9 = Dropout(0.2)(batch9)
    conv10 = Conv3D(256, (3,3,3), activation='relu', padding='same') (batch9)
    batch10 = BatchNormalization(axis=-1)(conv10)
    up2 = Conv3DTranspose(256, kernel_size=(2,2,2), strides=2) (batch10)

    concat2 = concatenate([up2, conv4])
    conv11 = Conv3D(128, (3,3,3), activation='relu', padding='same') (concat2)
    batch11 = BatchNormalization(axis=-1)(conv11)
    # batch11 = Dropout(0.2)(batch11)
    conv12 = Conv3D(128, (3,3,3), activation='relu', padding='same') (batch11)
    batch12 = BatchNormalization(axis=-1)(conv12)
    up3 = Conv3DTranspose(128, kernel_size=(2,2,2), strides=2) (batch12)

    concat3 = concatenate([up3, conv2])
    conv13 = Conv3D(64, (3,3,3), activation='relu', padding='same') (concat3)
    batch13 = BatchNormalization(axis=-1)(conv13)
    # batch13 = Dropout(0.2)(batch13)
    conv14 = Conv3D(64, (3,3,3), activation='relu', padding='same') (batch13)
    batch14 = BatchNormalization(axis=-1)(conv14)

    outputs = Conv3D(num_classes, (1, 1, 1), activation='softmax')(batch14)
    model = Model(inputs=[x], outputs=[outputs])
    return model


class DoubleConv(Model):
    def __init__(self, out_channels, kernel_size=3, strides=1, padding='same', batch_normal=True, dropout=0.2):
        super(DoubleConv, self).__init__()
        middle_conv_out_channels = out_channels // 2
        if out_channels % 2 != 0:
            logger.error(
                f"out_channels: {out_channels}, middle_conv_out_channels: "
                f"{middle_conv_out_channels},  The number of intermediate layer output channels of "
                f"double convolution is half of that of double convolution"
            )
            raise Exception("middle output channels of double convolution is error")

        self.doubleconv_model = Sequential([])
        self.doubleconv_model.add(
            Conv3D(middle_conv_out_channels, kernel_size=kernel_size, strides=strides, activation='relu',
                   padding=padding))
        if batch_normal:
            self.doubleconv_model.add(BatchNormalization(axis=-1))

        if dropout:
            self.doubleconv_model.add(Dropout(dropout))

        self.doubleconv_model.add(Conv3D(out_channels, kernel_size=kernel_size, activation='relu', padding=padding))

        if batch_normal:
            self.doubleconv_model.add(BatchNormalization(axis=-1))

    def call(self, x, training=None, *args, **kwargs):
        return self.doubleconv_model(x)


class DownSampling(Model):
    def __init__(self, kernel_size=2, strides=2):
        super(DownSampling, self).__init__()
        self.maxpool = MaxPooling3D(pool_size=kernel_size, strides=strides)

    def call(self, x, training=None, *args, **kwargs):
        return self.maxpool(x)


class UpSampling(Model):
    def __init__(self, in_channels, kernel_size=2, strides=2):
        super(UpSampling, self).__init__()
        self.up = Conv3DTranspose(in_channels, kernel_size=kernel_size, strides=strides)

    def call(self, x, training=None, *args, **kwargs):
        return self.up(x)


class LastConv(Model):
    def __init__(self, out_channels, act_function='softmax', kernel_size=1):
        super(LastConv, self).__init__()
        self.act_function = act_function
        self.conv = Conv3D(out_channels, kernel_size=kernel_size)
        self.classification = Activation(act_function)

    def call(self, x, training=None, *args, **kwargs):
        if self.act_function is None:
            logger.debug(
                f"active function is {self.act_function}, return last conv value, no calculate classification prob")
            return self.conv(x)
        else:
            logger.debug(f"active function is {self.act_function}, return classification prob")
            return self.classification(self.conv(x))


class DecodeDoubleConv(Model):
    def __init__(self, out_channels, kernel_size=3, strides=1, padding='same', batch_normal=True, dropout=0.2):
        super(DecodeDoubleConv, self).__init__()
        self.decoder_doubleconv_model = Sequential([])
        self.decoder_doubleconv_model.add(
            Conv3D(out_channels, kernel_size=kernel_size, strides=strides, activation='relu',
                   padding=padding))
        if batch_normal:
            self.decoder_doubleconv_model.add(BatchNormalization(axis=-1))

        if dropout:
            self.decoder_doubleconv_model.add(Dropout(dropout))

        self.decoder_doubleconv_model.add(
            Conv3D(out_channels, kernel_size=kernel_size, activation='relu', padding=padding))

        if batch_normal:
            self.decoder_doubleconv_model.add(BatchNormalization(axis=-1))

    def call(self, x, training=None, *args, **kwargs):
        logger.debug(f'decode double conv x shape: {x.shape}')
        res = self.decoder_doubleconv_model(x)
        logger.debug(f'decode double conv res shape: {res.shape}')
        return res


class UNet3D(Model):
    def __init__(self, conv3d_kernel_size=3, sample_kernel_size=2, conv3d_strides=1, sample_strides=2,
                 padding='same', num_classes=2, batch_normal=True, dropout=0.2):
        super(UNet3D, self).__init__()
        self.num_classes = num_classes
        self.batch_normal = batch_normal

        self.conv3d_kernel_size = conv3d_kernel_size
        self.conv3d_strides = conv3d_strides

        self.sample_kernel_size = sample_kernel_size
        self.sample_strides = sample_strides

        self.padding = padding
        self.num_classes = num_classes
        self.batch_normal = batch_normal
        self.dropout = dropout

        self.double_conv_1 = DoubleConv(64, kernel_size=self.conv3d_kernel_size,
                                        strides=self.conv3d_strides,
                                        padding=self.padding, batch_normal=self.batch_normal,
                                        dropout=self.dropout)
        self.downsample_1 = DownSampling(kernel_size=self.sample_kernel_size, strides=self.sample_strides)

        self.double_conv_2 = DoubleConv(128, kernel_size=self.conv3d_kernel_size,
                                        strides=self.conv3d_strides,
                                        padding=self.padding, batch_normal=self.batch_normal,
                                        dropout=self.dropout)
        self.downsample_2 = DownSampling(kernel_size=self.sample_kernel_size, strides=self.sample_strides)

        self.double_conv_3 = DoubleConv(256, kernel_size=self.conv3d_kernel_size,
                                        strides=self.conv3d_strides,
                                        padding=self.padding, batch_normal=self.batch_normal,
                                        dropout=self.dropout)
        self.downsample_3 = DownSampling(kernel_size=self.sample_kernel_size, strides=self.sample_strides)

        self.double_conv_4 = DoubleConv(512, kernel_size=self.conv3d_kernel_size,
                                        strides=self.conv3d_strides,
                                        padding=self.padding, batch_normal=self.batch_normal,
                                        dropout=self.dropout)

        self.upsample_1 = UpSampling(in_channels=512,
                                     kernel_size=self.sample_kernel_size,
                                     strides=self.sample_strides)
        self.decoder_doubleconv_1 = DecodeDoubleConv(out_channels=256,
                                                     kernel_size=self.conv3d_kernel_size, strides=self.conv3d_strides,
                                                     padding=self.padding, batch_normal=self.batch_normal,
                                                     dropout=self.dropout)

        self.upsample_2 = UpSampling(in_channels=256,
                                     kernel_size=self.sample_kernel_size,
                                     strides=self.sample_strides)
        self.decoder_doubleconv_2 = DecodeDoubleConv(out_channels=128,
                                                     kernel_size=self.conv3d_kernel_size, strides=self.conv3d_strides,
                                                     padding=self.padding, batch_normal=self.batch_normal,
                                                     dropout=self.dropout)

        self.upsample_3 = UpSampling(in_channels=128,
                                     kernel_size=self.sample_kernel_size,
                                     strides=self.sample_strides)
        self.decoder_doubleconv_3 = DecodeDoubleConv(out_channels=64,
                                                     kernel_size=self.conv3d_kernel_size, strides=self.conv3d_strides,
                                                     padding=self.padding, batch_normal=self.batch_normal,
                                                     dropout=self.dropout)

        self.classification = LastConv(out_channels=self.num_classes)

    def call(self, x, *args, **kwargs):
        logger.debug(f"input shape： {x.shape}")
        double_conv_1_val = self.double_conv_1(x)
        logger.debug(f"double_conv_1_val shape： {double_conv_1_val.shape}")
        downsample_1_val = self.downsample_1(double_conv_1_val)
        logger.debug(f"downsample_1_val shape： {downsample_1_val.shape}")

        double_conv_2_val = self.double_conv_2(downsample_1_val)
        logger.debug(f"double_conv_2_val shape： {double_conv_2_val.shape}")
        downsample_2_val = self.downsample_2(double_conv_2_val)
        logger.debug(f"downsample_2_val shape： {downsample_2_val.shape}")

        double_conv_3_val = self.double_conv_3(downsample_2_val)
        logger.debug(f"double_conv_3_val shape： {double_conv_3_val.shape}")
        downsample_3_val = self.downsample_3(double_conv_3_val)
        logger.debug(f"downsample_3_val shape： {downsample_3_val.shape}")

        double_conv_4_val = self.double_conv_4(downsample_3_val)
        logger.debug(f"double_conv_2_val shape： {double_conv_2_val.shape}")

        upsample_1_val = self.upsample_1(double_conv_4_val)
        decode_input_1 = K.concatenate([double_conv_3_val, upsample_1_val])
        decode_doubleconv_1_val = self.decoder_doubleconv_1(decode_input_1)
        logger.debug(
            f"upsample_1_val shape: {upsample_1_val.shape}, double_conv_3_val shape: {double_conv_3_val.shape}, decode_input_1 shape: {decode_input_1.shape}, decode_doubleconv_1_val shape: {decode_doubleconv_1_val.shape}")

        upsample_2_val = self.upsample_2(decode_doubleconv_1_val)
        decode_input_2 = K.concatenate([double_conv_2_val, upsample_2_val])
        decode_doubleconv_2_val = self.decoder_doubleconv_2(decode_input_2)
        logger.debug(
            f"upsample_2_val shape: {upsample_2_val.shape}, double_conv_2_val shape: {double_conv_2_val.shape}, decode_input_2 shape: {decode_input_2.shape}, decode_doubleconv_2_val shape: {decode_doubleconv_2_val.shape}")

        upsample_3_val = self.upsample_3(decode_doubleconv_2_val)
        decode_input_3 = K.concatenate([double_conv_1_val, upsample_3_val])
        decode_doubleconv_3_val = self.decoder_doubleconv_3(decode_input_3)
        logger.debug(
            f"upsample_3_val shape: {upsample_3_val.shape}, double_conv_1_val shape: {double_conv_1_val.shape}, decode_input_3 shape: {decode_input_3.shape}, decode_doubleconv_3_val shape: {decode_doubleconv_3_val.shape}")

        y_prob = self.classification(decode_doubleconv_3_val)
        logger.debug(f"y prob shape: {y_prob.shape}")

        return y_prob
