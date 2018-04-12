# -*- coding: utf-8 -*-
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import json
import common.settings
from cryptography.hazmat.primitives import serialization


# 128bits block size
class Encrypter():
    def aes_cbc_encrypt(self, message, key):
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

    def aes_cbc_decrypt(self, content, key):
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

    # 解密函数
    def decrypt_rsa(self, data, private_key_file_name = "local/chen.pem"):
        from cryptography.hazmat.primitives.asymmetric import padding
        """
        对原始数据文件使用指定的私钥进行解密，并将结果输出到目标文件中
        :param src_file_name: 原始数据文件
        :param dst_file_name: 解密输出文件
        :param private_key_file_name: 用于解密的私钥
        :return: 解密结果的bytes数组
        """
        # 读取原始数据
        # data_file = open(src_file_name, 'rb')
        # data = data_file.read()
        # data_file.close()

        # data = b'ZJ2vODjQbf7lNRhxFH70i9lg+FrhTKTvXDTPsovYoJauK9YL8uXmblD8AjKqVuEcNl3IxBJn6U4IcjqzN7upvbs6Un4n3iy9J4ovSsecQpj8HYtAxEiWZDxFLHc8JvwlKCVwFxoi7m8CZsy+w+tammeXSaWBc80f4oeSHA/iUlS2K4Dgw2Bi37uS5rojFCyi4OEnEOxjsoL4ia40tsEGPI/DTqnk6PICgy/SUZPXsBOF3iG+k+yolVXp9Vi31U2oI3D4Q+efYzA1ruT7nXixyPHjcfU+RAO09+oU3nzu+KnQFq5fBl+0d3pYS/xlcZUIHVjE9VXAewh0uSeDvbrxvQ=='

        # 读取私钥数据
        key_file = open(private_key_file_name, 'rb')
        key_data = key_file.read()
        key_file.close()

        # 从私钥数据中加载私钥
        private_key = serialization.load_pem_private_key(
            key_data,
            password=None,
            backend=default_backend()
        )

        data = base64.b64decode(data)

        # 使用私钥对数据进行解密，使用PKCS#1 v1.5的填充方式
        out_data = private_key.decrypt(
            data,
            padding.PKCS1v15()
        )
        sea_key = out_data.decode()[1:-1]

        # 将解密结果输出到目标文件中
        # out_data_file = open(dst_file_name, 'wb')
        # out_data_file.write(out_data)
        # out_data_file.close()

        # 返回解密结果
        return sea_key



if __name__ == '__main__':
    b = secretPassword()
    y = json.dumps({'secret': 'grtrgewfgvs', 'token': 'fye'})
    settings.logger.info('{}'.format(y))
    x = b.aes_cbc_encrypt('data=6902538006100&num=1&token=cb6aa5b6fbbd9acb155121c269c9f594&code=D8:9E:F3:1D:EE:7C&start=39.2799186706543&final=38.822940826416016')
    settings.logger.info('{}'.format(x))
    settings.logger.info('{}'.format(b.aes_cbc_decrypt(x)))
