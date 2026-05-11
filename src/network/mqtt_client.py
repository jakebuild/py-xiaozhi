import paho.mqtt.client as mqtt


class MqttClient:
    def __init__(
        self,
        server,
        port,
        username,
        password,
        subscribe_topic,
        publish_topic=None,
        client_id="PythonClient",
        on_connect=None,
        on_message=None,
        on_publish=None,
        on_disconnect=None,
    ):
        """Initialization MqttClient 实例。

        :param server: MQTT 服务器地址
        :param port: MQTT 服务器端口
        :param username: 登录用户名
        :param password: 登录密码
        :param subscribe_topic: 订阅的主题
        :param publish_topic: 发布的主题
        :param client_id: 客户端 ID，默认为 "PythonClient"
        :param on_connect: 自定义的Connect回调函数
        :param on_message: 自定义的消息接收回调函数
        :param on_publish: 自定义的消息发布回调函数
        :param on_disconnect: 自定义的DisconnectConnect回调函数
        """
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.subscribe_topic = subscribe_topic
        self.publish_topic = publish_topic
        self.client_id = client_id

        # 创建 MQTT 客户端实例，使用最新的API版本
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv5)

        # 设置用户名和密码
        self.client.username_pw_set(self.username, self.password)

        # 设置回调函数，如果提供了自定义回调函数，则使用自定义的，否则使用默认的
        if on_connect:
            self.client.on_connect = on_connect
        else:
            self.client.on_connect = self._on_connect

        self.client.on_message = on_message if on_message else self._on_message
        self.client.on_publish = on_publish if on_publish else self._on_publish

        if on_disconnect:
            self.client.on_disconnect = on_disconnect
        else:
            self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """
        默认的Connect回调函数。
        """
        if rc == 0:
            print("✅ SuccessConnect到 MQTT 服务器")
            # ConnectSuccess后，自动订阅主题
            client.subscribe(self.subscribe_topic)
            print(f"📥 已订阅主题：{self.subscribe_topic}")
        else:
            print(f"❌ Connection failed，Error码：{rc}")

    def _on_message(self, client, userdata, msg):
        """
        默认的消息接收回调函数。
        """
        topic = msg.topic
        content = msg.payload.decode()
        print(f"📩 收到消息 - 主题: {topic}，内容: {content}")

    def _on_publish(self, client, userdata, mid, properties=None):
        """
        默认的消息发布回调函数。
        """
        print(f"📤 消息已发布，消息 ID：{mid}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """
        默认的DisconnectConnect回调函数。
        """
        print("🔌 与 MQTT 服务器的Connect已Disconnect")

    def connect(self):
        """
        Connect到 MQTT 服务器。
        """
        try:
            self.client.connect(self.server, self.port, 60)
            print(f"🔗 Connecting到服务器 {self.server}:{self.port}")
        except Exception as e:
            print(f"❌ Connection failed，Error: {e}")

    def start(self):
        """
        Start客户端并开始网络循环。
        """
        self.client.loop_start()

    def publish(self, message):
        """
        发布消息到指定主题。
        """
        result = self.client.publish(self.publish_topic, message)
        status = result.rc
        if status == 0:
            print(f"✅ Success发布到主题 `{self.publish_topic}`")
        else:
            print(f"❌ 发布Failure，Error码：{status}")

    def stop(self):
        """
        Stop网络循环并DisconnectConnect。
        """
        self.client.loop_stop()
        self.client.disconnect()
        print("🛑 客户端已StopConnect")


if __name__ == "__main__":
    pass
    # 自定义的回调函数
    # def custom_on_connect(client, userdata, flags, rc, properties=None):
    #     if rc == 0:
    #         print("🎉 自定义回调：SuccessConnect到 MQTT 服务器")
    #         topic_data = userdata['subscribe_topic']
    #         client.subscribe(topic_data)
    #         print(f"📥 自定义回调：已订阅主题：{topic_data}")
    #     else:
    #         print(f"❌ 自定义回调：Connection failed，Error码：{rc}")
    #
    # def custom_on_message(client, userdata, msg):
    #     topic = msg.topic
    #     content = msg.payload.decode()
    #     print(f"📩 自定义回调：收到消息 - 主题: {topic}，内容: {content}")
    #
    # def custom_on_publish(client, userdata, mid, properties=None):
    #     print(f"📤 自定义回调：消息已发布，消息 ID：{mid}")
    #
    # def custom_on_disconnect(client, userdata, rc, properties=None):
    #     print("🔌 自定义回调：与 MQTT 服务器的Connect已Disconnect")
    #
    # # 创建 MqttClient 实例，传入自定义的回调函数
    # mqtt_client = MqttClient(
    #     server="8.130.181.98",
    #     port=1883,
    #     username="admin",
    #     password="dtwin@123",
    #     subscribe_topic="sensors/temperature/request",
    #     publish_topic="sensors/temperature/device_001/state",
    #     client_id="CustomClient",
    #     on_connect=custom_on_connect,
    #     on_message=custom_on_message,
    #     on_publish=custom_on_publish,
    #     on_disconnect=custom_on_disconnect
    # )
    #
    # # 将订阅主题信息作为用户数据传递给回调函数
    # mqtt_client.client.user_data_set(
    #     {'subscribe_topic': mqtt_client.subscribe_topic}
    # )
    #
    # # Connect到 MQTT 服务器
    # mqtt_client.connect()
    #
    # # Start客户端
    # mqtt_client.start()
    #
    # try:
    #     while True:
    #         # 发布消息
    #         message = input("输入要发布的消息：")
    #         mqtt_client.publish(message)
    # except KeyboardInterrupt:
    #     print("\n⛔️ 程序已Stop")
    # finally:
    #     # Stop并DisconnectConnect
    #     mqtt_client.stop()
