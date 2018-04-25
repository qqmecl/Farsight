# -*- coding: utf-8 -*-
import serial
import time
import common.settings as settings


class Screen:
    WELCOME_PAGE = [0x00]
    INVENTORY_PAGE = [0x01]
    PROCESSING_PAGE = [0x02]
    THANK_PAGE = [0x03]
    DEBUG_PAGE = [0x04]

    APPEND_ITEM = [0x02]
    CLEAR_CART_LIST = [0x03]
    UPDATE_CART_PRICE = [0x04]
    CLEAR_CART_PRICE = [0x05]
    UPDATE_CART_NUMBER = [0x06]
    CLEAR_CART_NUMBER = [0x07]
    m_drink_Dic = {}
    m_commodity_Dic = {}
    m_total_number = 0
    m_total_price = 0
    def __init__(self, port=settings.screen_port):
        rate = 9600  # 当前串口通信设备波特率
        # rate = 115200  # 当前串口通信设备波特率
        self.com = serial.Serial(port, baudrate=rate)
        self.m_current_page = self.WELCOME_PAGE
        self.change_to_page(self.m_current_page)
        self.close()
    def resetData(self):
        self.curItems = [] 

    def change_to_page(self, page):
        self.m_current_page = page
        if page == self.INVENTORY_PAGE: 
            self.close()
        elif page == self.THANK_PAGE:
            self.close()
        data = [0xA0, 0x90,0x01,0x00,0x01] + page +[0xFF, 0xFC, 0xFF, 0xFF]
        self.com.write(data)

    def Init_item_info(self,order,goodsName,price,number):
        m_head = [0xA0, 0x90]
        m_tail = [0xFF, 0xFC, 0xFF, 0xFF]
        m_data = self.get_goods_Info_hex(goodsName)
        m_info = self.get_info_hex(str(price),str(number))
        m_datalen = [*divmod(len(m_data + m_info), 256)]
        m_allData = m_head + order + m_datalen + m_data + m_info + m_tail
        return m_allData

    def Add_item(self, name, price, number, order = [0x02]):
        #print(self.m_current_page)
        if self.m_current_page != self.INVENTORY_PAGE:
            #print("return")
            return
        if self.m_commodity_Dic.get(name) == None:
           # print("Add OK")
            data = self.Init_item_info(order,name,price,number)

            info = [data,price,number]
            #print("ADD",self.ByteToHex(data))
            self.m_commodity_Dic[name] = info
        else:
            self.m_commodity_Dic[name][2] += number
            self.Update_item_info(order,name,price,self.m_commodity_Dic[name][2])
        self.m_total_price += price
        self.m_total_number += number
        self.Update_show()

    def Update_item_info(self,order,key,price,number):
        if self.m_commodity_Dic.get(key) != None:
            self.m_commodity_Dic[key][2] = int(number)
            data = self.Init_item_info(order,key, price,str(self.m_commodity_Dic[key][2]))
            #print("ADD",data)
            self.m_commodity_Dic[key][0] = data
        #return 

    def get_goods_Info_hex(self, name):
        if self.m_drink_Dic.get(name) == None:
            data_bytes = name.encode(encoding='utf-8')
            data = []
            for i in data_bytes:
                data.append(i)
            else:
                self.m_drink_Dic[name] = data
                return data
        else:
            return self.m_drink_Dic.get(name)

        #return price and number  hex

    def get_info_hex(self, price,number):
        m_line = [0x2D]
        #print(hex(int(number)))
        m_number = number.encode(encoding = 'utf-8')
        #print(self.ByteToHex(m_number))
        m_price = price.encode(encoding='utf-8')
        number_ls = []
        price_ls = []
        for i in m_number:
            number_ls.append(i)
        for i in m_price:
            price_ls.append(i)
        data = m_line + price_ls + m_line + number_ls
        #print("info",self.ByteToHex(data))
        return data

    def ByteToHex(self, bins):
        data = []
        for x in bins:
            data.append(('0x%02X' % x).strip())
        return data
    #update info or clear info
    def Update_or_clear(self,order,number = ""):
        m_head = [0xA0, 0x90]
        data = number.encode(encoding = 'utf-8')
        data_ls = []
        for i in data:
            data_ls.append(i)
        m_datalen = [*divmod(len(data), 256)]
        m_tail = [0xFF, 0xFC, 0xFF, 0xFF]
        m_all = m_head + order + m_datalen + data_ls + m_tail
        #print(self.ByteToHex(m_all))
        self.com.write(m_all)
    # update show info
    def Update_show(self):
        self.Update_or_clear(self.CLEAR_CART_LIST)
        self.Update_or_clear(self.UPDATE_CART_PRICE,str(round(self.m_total_price, 1)))
        self.Update_or_clear(self.UPDATE_CART_NUMBER,str(self.m_total_number))
        for key in self.m_commodity_Dic:
            #print("Update show",self.ByteToHex(self.m_commodity_Dic[key][0]))
            self.com.write(self.com.write(self.m_commodity_Dic[key][0]))

    def remove_item(self, name, number, order = [0x02]):
        #print("remove_item")
        if self.m_commodity_Dic.get(name) == None:
            return
        m_number = self.m_commodity_Dic[name][2] - number
        m_price = self.m_commodity_Dic[name][1]
        if m_number <= 0:
            #print(m_number)
            #print(number)
            value = number + m_number
            #print(value)
            m_price = self.m_commodity_Dic[name][1] * value
            self.m_total_number -= value
            self.m_total_price -= m_price
            self.m_commodity_Dic.pop(name)
        else:
            self.m_total_number -= number
            self.m_total_price -= m_price
            #print("m_total_number",self.m_total_number)
            #print("m_total_price",self.m_total_number)
            self.Update_item_info(order,name,str(m_price),str(m_number))
        self.Update_show()
    #clear info
    def close(self):
        self.Update_or_clear(self.CLEAR_CART_LIST)
        self.Update_or_clear(self.CLEAR_CART_NUMBER)
        self.Update_or_clear(self.CLEAR_CART_PRICE)
        self.m_commodity_Dic.clear()
        self.m_total_price = 0
        self.m_total_number = 0
        # print("close(self):")
    
    def Debug(self):
        while True:
            number = input("please input index")
            last = time.time()
            if number == '1':
                screen.change_to_page(screen.WELCOME_PAGE)
            elif number == '2':
                screen.change_to_page(screen.INVENTORY_PAGE)
            elif number == '3':
                screen.change_to_page(screen.PROCESSING_PAGE)
            elif number == '4':
                screen.change_to_page(screen.THANK_PAGE)
            elif number == '5':
                screen.change_to_page(screen.DEBUG_PAGE)
            elif number == '7':
                screen.Add_item("康师傅果粒橙", 5.0, 1)
            elif number == '8':
                screen.Add_item("农夫山泉", 4, 1)
            elif number == 'q':
                number = int(input("please input remove number"))
                last = time.time()
                screen.remove_item("康师傅果粒橙",number)
            elif number == '0':
                break
            else:
                continue
            print(time.time()-last)
        self.close()
if __name__ == '__main__':
    screen = Screen()
    screen.Debug()