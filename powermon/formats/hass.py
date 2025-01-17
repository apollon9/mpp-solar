import json as js
import logging
from datetime import datetime
from powermon.formats.abstractformat import AbstractFormat
from powermon.commands.result import Result
from powermon.commands.response import Response

log = logging.getLogger("hass")


class hass(AbstractFormat):
    def __init__(self, formatConfig, device):
        super().__init__(formatConfig)
        self.name = "hass"
        self.extra_info = formatConfig.get("extra_info", False)
        self.discovery_prefix = formatConfig.get("discovery_prefix", "homeassistant")
        self.entity_id_prefix = formatConfig.get("entity_id_prefix", "mpp")
        if device is None:
            self.device_name = "MPP Solar"
            self.device_id = "mpp-solar"
            self.device_model = "MPP Solar"
            self.device_manufacturer = "MPP Solar"
        else:
            self.device_name = device.name
            self.device_id = device.device_id
            self.device_model = device.model
            self.device_manufacturer = device.manufacturer

    def sendsMultipleMessages(self) -> bool:
        return True
    
    def set_command_description(self, command_description):
        pass

    def format(self, result: Result) -> list:
        log.info("Using output formatter: %s" % self.name)

        config_msgs = []
        value_msgs = []

        _result = []
        if result.responses is None:
            return _result
        display_data : list[Response] = self.format_and_filter_data(result)
        log.debug(f"displayData: {display_data}")

        # build data to display
        for response in display_data:
            # Get key data
            data_name = response.get_data_name()
            value = response.get_data_value()
            unit = response.get_data_unit()
            icon = response.get_icon()
            device_class = response.get_device_class()
            state_class = response.get_state_class()

            # Set component type
            if unit == "bool" or value == "enabled" or value == "disabled":
                component = "binary_sensor"
            else:
                component = "sensor"

            # Make value adjustments
            if component == "binary_sensor":
                if value == 0 or value == "0" or value == "disabled":
                    value = "OFF"
                elif value == 1 or value == "1" or value == "enabled":
                    value = "ON"


            # Object ID
            object_id = f"{self.entity_id_prefix}_{data_name}".lower()

            name = f"{self.entity_id_prefix} {data_name}"

            # Home Assistant MQTT Auto Discovery Message
            #
            # Topic
            # <discovery_prefix>/<component>/[<node_id>/]<object_id>/config, eg homeassistant/binary_sensor/garden/config
            topic_base = f"{self.discovery_prefix}/{component}/{object_id}".replace(" ", "_")
            topic = f"{topic_base}/config"
            state_topic = f"{topic_base}/state"

            # Payload
            # msg '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/binary_sensor/garden/state", "unit_of_measurement": "°C", "icon": "power-plug"}'
            payload = {
                "name": f"{name}",
                "state_topic": f"{state_topic}",
                "unique_id": f"{object_id}",
                "force_update": "true",
                "last_reset": str(datetime.now()),
            }

            # Add device info
            # payload["device"] = {"name": f"{device_name}", "identifiers": ["mppsolar"], "model": "PIP6048MAX", "manufacturer": "MPP-Solar"}
            payload["device"] = {
                "name": self.device_name,
                "identifiers": [self.device_id],
                "model": self.device_model,
                "manufacturer": self.device_manufacturer,
            }

            # Add unit of measurement
            if unit and unit != "bool":
                payload["unit_of_measurement"] = f"{unit}"

            # Add icon
            if icon:
                payload.update({"icon": icon})

            # Add device class
            if device_class:
                payload["device_class"] = device_class

            # Add state_class
            if state_class:
                payload["state_class"] = state_class

            payloads = js.dumps(payload)
            # print(payloads)
            msg = {"topic": topic, "payload": payloads}
            config_msgs.append(msg)

            # VALUE SETTING
            msg = {"topic": state_topic, "payload": value}
            value_msgs.append(msg)

        # order value msgs after config to allow HA time to build entity before state data arrives
        return config_msgs + value_msgs
