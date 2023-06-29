import json

import openai
import plugins
import os

from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from plugins import *
from common.log import logger
from plugins.NewGpt import function as fun


@plugins.register(name="NewGpt", desc="GPT函数调用，实现联网", desire_priority=99, version="0.1", author="chazzjimel", )
class NewGpt(Plugin):
    def __init__(self):
        super().__init__()
        self.count_max_tokens = None
        self.max_tokens = None
        self.temperature = None
        self.functions_openai_model = None
        self.assistant_openai_model = None
        self.app_sign = None
        self.app_key = None
        self.bing_subscription_key = None
        self.alapi_key = None
        self.prompt = None
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "config.json")
        logger.info(f"[NewGpt] current directory: {curdir}")
        logger.info(f"加载配置文件: {config_path}")
        logger.info("[NewGpt] inited")
        if not os.path.exists(config_path):
            logger.info('[RP] 配置文件不存在，将使用config.json.template模板')
            config_path = os.path.join(curdir, "config.json.template")
            logger.info(f"[NewGpt] config template path: {config_path}")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT
        ]:
            return
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.debug(f"[NewGpt] config content: {config}")
                self.alapi_key = config["alapi_key"]
                self.bing_subscription_key = config["bing_subscription_key"]
                self.functions_openai_model = config["functions_openai_model"]
                self.assistant_openai_model = config["assistant_openai_model"]
                self.app_key = config["app_key"]
                self.app_sign = config["app_sign"]
                self.temperature = config.get("temperature", 0.9)
                self.max_tokens = config.get("max_tokens", 1000)
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                logger.warn(f"[RP] init failed, config.json not found.")
            else:
                logger.warn("[RP] init failed." + str(e))
            raise e
        reply = Reply()  # 创建一个回复对象
        content = e_context['context'].content[:]  # 获取内容
        if "help" in content or "帮助" in content:  # 如果用户请求帮助
            reply.type = ReplyType.INFO
            reply.content = self.get_help_text(verbose=True)
        else:
            context = e_context['context'].content[:]
            conversation_output = self.run_conversation(context, e_context)
            if conversation_output is not None:
                reply = Reply()  # 创建一个回复对象
                reply.type = ReplyType.TEXT
                reply.content = conversation_output
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
            else:
                return

    def run_conversation(self, context, e_context: EventContext):
        global function_response
        messages = []
        content = context
        logger.debug(f"User input: {content}")  # 用户输入

        messages.append({
            "role": "user",
            "content": content
        })

        response = openai.ChatCompletion.create(
            model=self.functions_openai_model,
            messages=messages,
            functions=[
                {
                    "name": "get_current_weather",
                    "description": "获取指定城市的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "Cities with Chinese names, for example: 广州, 深圳",
                            },

                        },
                        "required": ["city"],
                    },
                },
                {
                    "name": "get_morning_news",
                    "description": "获取新闻早报",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_hotlist",
                    "description": "获取各种热榜信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "type类型: '知乎':zhihu', '微博':weibo', '微信':weixin', '百度':baidu', '头条':toutiao', '163':163', 'xl', '36氪':36k', 'hitory', 'sspai', 'csdn', 'juejin', 'bilibili', 'douyin', '52pojie', 'v2ex', 'hostloc'",
                            }
                        },
                        "required": ["type"],
                    }
                },
                {
                    "name": "search_bing",
                    "description": "必应搜索引擎，本函数需要有明确包含'搜索'的指令内容才可以调用",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "提供需要搜索的关键词信息",
                            },
                            "count": {
                                "type": "string",
                                "description": "搜索页数,如无指定几页，默认3",
                            }

                        },
                        "required": ["query", "count"],
                    },
                },
                {
                    "name": "get_oil_price",
                    "description": "获取全国油价信息",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_Constellation_analysis",
                    "description": "获取星座运势",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "star": {
                                "type": "string",
                                "description": """星座英文        
                                        "白羊座": "aries",
                                        "金牛座": "taurus",
                                        "双子座": "gemini",
                                        "巨蟹座": "cancer",
                                        "狮子座": "leo",
                                        "处女座": "virgo",
                                        "天秤座": "libra",
                                        "天蝎座": "scorpio",
                                        "射手座": "sagittarius",
                                        "摩羯座": "capricorn",
                                        "水瓶座": "aquarius",
                                        "双鱼座": "pisces"""
                            },

                        },
                        "required": ["star"],
                    },
                },
                {
                    "name": "music_search",
                    "description": "音乐搜索，获得音乐信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "需要搜索的音乐关键词信息",
                            },

                        },
                        "required": ["keyword"],
                    },
                },
                {
                    "name": "get_datetime",
                    "description": "获取指定城市实时日期时间和星期信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city_en": {
                                "type": "string",
                                "description": "需要查询的城市小写英文名，英文名中间空格用-代替，如beijing，new-york",
                            },

                        },
                        "required": ["city_en"],
                    },
                },
                {
                    "name": "get_url",
                    "description": "获取指定URL的内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "需要访问的指定URL",
                            },

                        },
                        "required": ["url"],
                    },
                },
            ],
            function_call="auto",
        )

        message = response["choices"][0]["message"]

        # 检查模型是否希望调用函数
        if message.get("function_call"):
            function_name = message["function_call"]["name"]
            logger.debug(f"Function call: {function_name}")  # 打印函数调用
            logger.debug(f"message={message}")

            # 处理各种可能的函数调用，执行函数并获取函数的返回结果
            if function_name == "get_current_weather":
                function_args = json.loads(message["function_call"].get("arguments", "{}"))
                logger.debug(f"Function arguments: {function_args}")  # 打印函数参数

                function_response = fun.get_current_weather(api_key=self.alapi_key,
                                                            city=function_args.get("city", "未指定地点"),
                                                            )
                function_response = json.dumps(function_response, ensure_ascii=False)
                logger.debug(f"Function response: {function_response}")  # 打印函数响应

            elif function_name == "get_morning_news":
                function_response = fun.get_morning_news(api_key=self.alapi_key)
                logger.debug(f"Function response: {function_response}")  # 打印函数响应

            elif function_name == "get_hotlist":
                function_args_str = message["function_call"].get("arguments", "{}")
                function_args = json.loads(function_args_str)  # 使用 json.loads 将字符串转换为字典
                hotlist_type = function_args.get("type", "未指定类型")
                function_response = fun.get_hotlist(api_key=self.alapi_key, type=hotlist_type)
                function_response = json.dumps(function_response, ensure_ascii=False)
                logger.debug(f"Function response: {function_response}")  # 打印函数响应

            elif function_name == "search_bing":
                function_args_str = message["function_call"].get("arguments", "{}")
                function_args = json.loads(function_args_str)  # 使用 json.loads 将字符串转换为字典
                search_query = function_args.get("query", "未指定关键词")
                search_count = function_args.get("count", 3)
                if "搜索" in content or "必应" in content or "newbing" in content.lower():
                    function_response = fun.search_bing(subscription_key=self.bing_subscription_key, query=search_query,
                                                        count=search_count,
                                                        endpoint="https://api.bing.microsoft.com/v7.0/search")
                    function_response = json.dumps(function_response, ensure_ascii=False)
                    logger.debug(f"Function response: {function_response}")  # 打印函数响应
                else:
                    return None
            elif function_name == "get_oil_price":
                function_response = fun.get_oil_price(api_key=self.alapi_key)
                logger.debug(f"Function response: {function_response}")  # 打印函数响应
            elif function_name == "get_Constellation_analysis":
                function_args = json.loads(message["function_call"].get("arguments", "{}"))
                logger.debug(f"Function arguments: {function_args}")  # 打印函数参数

                function_response = fun.get_Constellation_analysis(api_key=self.alapi_key,
                                                                   star=function_args.get("star", "未指定星座"),
                                                                   )
                function_response = json.dumps(function_response, ensure_ascii=False)
                logger.debug(f"Function response: {function_response}")  # 打印函数响应
            elif function_name == "music_search":
                function_args = json.loads(message["function_call"].get("arguments", "{}"))
                logger.debug(f"Function arguments: {function_args}")  # 打印函数参数

                function_response = fun.music_search(api_key=self.alapi_key,
                                                     keyword=function_args.get("keyword", "未指定音乐"),
                                                     )
                function_response = json.dumps(function_response, ensure_ascii=False)
                logger.debug(f"Function response: {function_response}")  # 打印函数响应
            elif function_name == "get_datetime":
                function_args = json.loads(message["function_call"].get("arguments", "{}"))
                logger.debug(f"Function arguments: {function_args}")  # 打印函数参数
                city = function_args.get("city_en", "beijing")  # 如果没有指定城市，将默认查询北京
                function_response = fun.get_datetime(appkey=self.app_key, sign=self.app_sign, city_en=city)
                function_response = json.dumps(function_response, ensure_ascii=False)
                logger.debug(f"Function response: {function_response}")  # 打印函数响应
            elif function_name == "get_url":
                function_args = json.loads(message["function_call"].get("arguments", "{}"))
                logger.debug(f"Function arguments: {function_args}")  # 打印函数参数
                url = function_args.get("url", "未指定URL")  # 如果没有指定城市，将默认查询北京
                function_response = fun.get_url(url=url)
                function_response = json.dumps(function_response, ensure_ascii=False)
                logger.debug(f"Function response: {function_response}")  # 打印函数响应


            msg: ChatMessage = e_context["context"]["msg"]
            if e_context["context"]["isgroup"]:
                self.prompt = f"你是'{msg.to_user_nickname}'，你主要负责帮'{msg.actual_user_nickname}'使用各种工具完成用户想要得到的信息，如果没有指定语言，请和'{msg.from_user_nickname}'打招呼，发挥随机风格总结内容并使用中文交流。"
            else:
                self.prompt = f"你是'{msg.to_user_nickname}'，你主要负责帮'{msg.from_user_nickname}'使用各种工具完成用户想要得到的信息，如果没有指定语言，请和'{msg.from_user_nickname}'打招呼，发挥随机风格总结内容并使用中文告诉用户。"
            # 将函数的返回结果发送给第二个模型
            logger.debug(f"prompt :" + self.prompt)
            second_response = openai.ChatCompletion.create(
                model=self.assistant_openai_model,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": content},
                    message,
                    {"role": "assistant", "content": function_response, },
                ],
                temperature=float(self.temperature),
                max_tokens=int(self.max_tokens)
            )

            logger.debug(f"Second response: {second_response['choices'][0]['message']['content']}")  # 打印第二次的响应
            messages.append(second_response["choices"][0]["message"])
            return second_response['choices'][0]['message']['content']

        else:
            # 如果模型不希望调用函数，直接打印其响应
            logger.debug(f"Model response: {message['content']}")  # 打印模型的响应
            return message['content']

    def get_help_text(self, verbose=False, **kwargs):
        # 初始化帮助文本，说明利用 midjourney api 来画图
        help_text = "GPT函数调用，实现联网\n"
        # 如果不需要详细说明，则直接返回帮助文本
        if not verbose:
            return help_text
        # 否则，添加详细的使用方法到帮助文本中
        help_text = "NewGpt无需特殊指令，插件前置识别，支持早报、天气、油价、星座、音乐（网易云）、各类热榜信息等"
        # 返回帮助文本
        return help_text
