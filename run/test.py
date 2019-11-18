
import hashlib
import json
from requests import request

from libs.utils.exceptions import PubErrorCustom
from libs.utils.mytime import UtilTime
from libs.utils.string_extension import md5pass

class CreateOrderForLastPass(object):

    def __init__(self,**kwargs):

        #规则
        self.rules = kwargs.get("rules"),None

        #传入数据
        self.data = kwargs.get("data"),None

        #请求数据
        self.request_data = None

        #参加签名数据
        self.request_data_sign = None

        #返回数据
        self.response = None

    #数据整理
    def dataHandler(self,data):
        for item in self.rules.get("requestData"):
            if 'value' in item:
                item['value'] = data.get(item['value']) if item.get("type") == "appoint" else item['value']
            res = getattr(CustDateType, "get_{}".format(item['dataType']))(item)

            self.request_data[item['key']] = res
            if item.get("sign",None) :
                self.request_data_sign[item['key']] = res

    #签名
    def signHandler(self,signRules):
        sign = SignBase(
            hashData=self.request_data_sign,
            signRules=signRules
        ).run()
        self.request_data[signRules['signKey']] = sign

    #向上游发起请求
    def requestHandlerForJson(self):
        """
        "request":{
            "url":"http://localhost:8000",
            "method" : "POST",
            "type":"json",
        },
        """
        if self.rules.get("request").get("type") == 'json':
            result = request(
                url=self.rules.get("request").get("url"),
                method=self.rules.get("request").get("method"),
                json = self.request_data,
                headers={
                    "Content-Type": 'application/json'
                }
            )
        elif self.rules.get("request").get("type") == 'body':
            result = request(
                url = self.rules.get("request").get("url"),
                method = self.rules.get("request").get("method"),
                data=self.request_data,
            )
        elif self.rules.get("request").get("type") == 'params':
            result = request(
                url = self.rules.get("request").get("url"),
                method = self.rules.get("request").get("method"),
                params=self.request_data,
            )
        else:
            raise PubErrorCustom("请求参数错误!")

        try :
            self.response = json.loads(result.content.decode('utf-8'))
        except Exception as e:
            raise PubErrorCustom("返回JSON错误!{}".format(result.text))

    #返回数据json映射
    def rDataMapForJson(self):
        # 返回数据映射
        str = ""
        for (index, item) in enumerate(self.rules.get("return").get("url").split(".")):
            str = str + "['{}".format(item) if index == 0 else str + "']['{}".format(item)
        str += "']"

        return eval("self.response{}".format(str))

    #返回数据
    def responseHandlerForJson(self):
        if str(self.response.get(self.rules.get("return").get("codeKey"))) != str(self.rules.get("return").get("ok")):
            raise PubErrorCustom(self.response.get(self.rules.get("return").get("msgKey")))
        return self.rDataMapForJson()

    #向上游发起请求
    def requestHandlerForHtml(self):
        pass

    #返回html时处理
    def responseHandlerForHtml(self):
        return "http://localhost:8000/api/{}".format(md5pass(self.data.get("ordercode")))

    def runForJson(self):
        self.dataHandler(self.data)
        self.signHandler(self.rules.get("sign"))
        self.requestHandlerForJson()
        return self.responseHandlerForJson()

    def runForHtml(self):
        self.responseHandlerForHtml()

    def run(self):
        if self.rules.get("return").get("type") == 'json':
            self.runForJson()
        else:
            self.runForHtml()


class CustDateType(object):

    @staticmethod
    def get_amount(obj):
        if obj['unit'] == 'F':
            return "%.{}lf".format(int(obj['point'])) % (float(obj['value']) * 100.0)
        elif obj['unit'] == 'Y':
            return "%.{}lf".format(int(obj['point'])) % (float(obj['value']))
        else:
            raise PubErrorCustom("标志错误!")

    @staticmethod
    def get_date(obj):
        if obj.get("type") == "appoint":
            return obj.get("value")
        else:
            ut = UtilTime()
            return ut.timestamp \
                if obj.get("format", None) == 'timestamp' else \
                ut.arrow_to_string(arrow_s=ut.today, format_v=obj.get("format", None)) if obj.get("format", None) \
                    else ut.arrow_to_string(arrow_s=ut.today)

    @staticmethod
    def get_string(obj):
        return str(obj.get("value"))

    @staticmethod
    def get_int(obj):
        return int(obj.get("value"))

class SignBase(object):

    def __init__(self,**kwargs):

        #需要加密的值
        self.hashData = kwargs.get("hashData",None)

        #加密规则
        self.signRules = kwargs.get("signRules",None)

    def hashBeforeHandler(self):

        #按字典key ascii码排序 并过滤空值
        if self.signRules["signDataType"] == 'key-ascii-sort':
            str = ""
            for item in sorted({k: v for k, v in self.hashData.items() if v != ""}):
                str += str(self.hashData[item])
            if self.signRules.get("signAppend", None):
                str="{}{}".format(str,self.signRules["signAppend"].format(**self.hashData))
            if self.signRules.get("signBefore", None):
                str="{}{}".format(self.signRules["signBefore"].format(**self.hashData),str)

            return str

        #按指定key排序
        elif  self.signRules["signDataType"] == 'key-appoint':
            return self.signRules["signValue"].format(**self.hashData)

    def md5(self):
        signData = self.hashBeforeHandler()
        return hashlib.md5(signData.encode(self.signRules['signEncode'])).hexdigest().upper() \
            if self.signRulesget.get('dataType',None) == 'upper' else hashlib.md5(signData.encode(self.signRules['signEncode'])).hexdigest()

    def run(self):
        return getattr(self,self.signRules['signType'])()


if __name__ == '__main__':
    CreateOrderForLastPass().run()