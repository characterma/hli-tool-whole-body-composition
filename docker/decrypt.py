from __future__ import print_function
import boto3
import base64


kms_client = boto3.client("kms")

with open("key.kms", 'rU') as inFile:
    encrypted_key = inFile.read()

cypher_text = base64.b64decode(encrypted_key)
key = kms_client.decrypt(CiphertextBlob=cypher_text)['Plaintext']
print(key.decode('utf8'))
