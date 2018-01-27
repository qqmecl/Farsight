# -*- coding: utf-8 -*-

import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import uuid

def get_mac_address(): 
	mac=uuid.UUID(int = uuid.getnode()).hex[-12:].upper()
	return ":".join([mac[e:e+2] for e in range(0,11,2)])

# 128bits block size
class secretPassword():
    def aes_cbc_encrypt(self, message, key = '20607etgrttplant'):
        '''
        use AES CBC to encrypt message, using key and init vector
        :param message: the message to encrypt
        :param key: the secret
        :return: bytes init_vector + encrypted_content
        '''
        iv_len = 16
        aes_block_size = 16
        assert type(message) in (str,bytes)
        assert type(key) in (str,bytes)
        if type(message) == str:
            message = bytes(message, 'utf-8')
        if type(key) == str:
            key = bytes(key, 'utf-8')
        backend = default_backend()
        iv = b'1234567890123412'
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(message) + padder.finalize()
        enc_content = encryptor.update(padded_data) + encryptor.finalize()
        b64 = base64.b64encode(enc_content)
        return b64.decode()
    
    def aes_cbc_decrypt(self, content, key = '20607etgrttplant'):
        '''
        use AES CBC to decrypt message, using key
        :param content: the encrypted content using the above protocol
        :param key: the secret
        :return: decrypted bytes
        '''
        aes_block_size = 16
        content = content.encode(encoding="utf-8")
        content = b'1234567890123412' + base64.b64decode(content)
        assert type(content) == bytes
        assert type(key) in (bytes, str)
        if type(key) == str:
            key = bytes(key, 'utf-8')
        iv_len = 16
        assert len(content) >= (iv_len + 16)
        iv = content[:iv_len]
        enc_content = content[iv_len:]
        backend = default_backend()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
        unpadder = padding.PKCS7(128).unpadder()
        decryptor = cipher.decryptor()
        dec_content = decryptor.update(enc_content) + decryptor.finalize()
        real_content = unpadder.update(dec_content) + unpadder.finalize()
        return real_content.decode()

    

if __name__ == '__main__':
    b = secretPassword()
    x = b.aes_cbc_encrypt('secret=dfss&side=fgd&num=1&token=fgdf&itemId=yrthyt')
    print(x)
    print(b.aes_cbc_decrypt(x))
