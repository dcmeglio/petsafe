import json
from typing import Optional

from .const import (
    SMARTDOOR_FINAL_ACT_LOCKED,
    SMARTDOOR_FINAL_ACT_UNLOCKED,
    SMARTDOOR_MODE_MANUAL_LOCKED,
    SMARTDOOR_MODE_MANUAL_UNLOCKED,
    SMARTDOOR_MODE_SMART,
)


class DeviceSmartFeed:
    def __init__(self, client, data: dict):
        """
        PetSafe SmartFeed device.

        :param client: PetSafeClient with authorization tokens
        :param data: data regarding feeder
        """
        self.client = client
        self.data = data

    def __str__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        """
        All feeder data formatted as JSON.

        """
        return json.dumps(self.data, indent=2)

    async def update_data(self) -> None:
        """
        Updates self.data to the feeder's current online state.

        """
        response = await self.client.api_get(self.api_path)
        response.raise_for_status()
        self.data = json.loads(response.content.decode("UTF-8"))

    async def put_setting(
        self, setting: str, value, force_update: bool = False
    ) -> None:
        """
        Changes the value of a specified setting. Sends PUT to API.

        :param setting: the setting to change
        :param value: the new value of that setting
        :param force_update: if True, update ALL data after PUT. Defaults to False.

        """
        response = await self.client.api_put(
            self.api_path + "settings/" + setting, data={"value": value}
        )
        response.raise_for_status()

        if force_update:
            await self.update_data()
        else:
            self.data["settings"][setting] = value

    async def get_messages_since(self, days: int = 7):
        """
        Requests all feeder messages.

        :param days: how many days to request back. Defaults to 7.
        :return: the APIs response in JSON.

        """
        response = await self.client.api_get(
            self.api_path + "messages?days=" + str(days)
        )
        response.raise_for_status()
        return json.loads(response.content.decode("UTF-8"))

    async def get_last_feeding(self):
        """
        Finds the last feeding in the feeder's messages.

        :return: the feeding message, if found. Otherwise, None.

        """
        messages = await self.get_messages_since()
        for message in messages:
            if message["message_type"] == "FEED_DONE":
                return message
        return None

    async def feed(
        self, amount: int = 1, slow_feed: bool = None, update_data: bool = True
    ) -> None:
        """
        Triggers the feeder to begin feeding.

        :param amount: the amount to feed in 1/8 increments.
        :param slow_feed: if True, will use slow feeding. If None, defaults to current settings.
        :param update_data: if True, will update the feeder's data after feeding. Defaults to True.

        """
        if slow_feed is None:
            slow_feed = self.data["settings"]["slow_feed"]
        response = await self.client.api_post(
            self.api_path + "meals", data={"amount": amount, "slow_feed": slow_feed}
        )
        response.raise_for_status()

        if update_data:
            await self.update_data()

    async def repeat_feed(self) -> None:
        """
        Repeats the last feeding.

        """
        last_feeding = await self.get_last_feeding()
        await self.feed(last_feeding["amount"])

    async def prime(self) -> None:
        """
        Feeds 5/8 cups to prime the feeder.

        """
        await self.feed(5, False)

    async def get_schedules(self):
        """
        Requests all feeding schedules.

        :return: the APIs response in JSON.

        """
        response = await self.client.api_get(self.api_path + "schedules")
        response.raise_for_status()
        return json.loads(response.content.decode("UTF-8"))

    async def schedule_feed(
        self, time: str = "00:00", amount: int = 1, update_data: bool = True
    ):
        """
        Adds time and feed amount to schedule.

        :param time: the time to dispense the food in 24 hour notation with colon separation (e.g. 16:35 for 4:35PM)
        :param amount: the amount to feed in 1/8 increments.
        :param update_data: if True, will update the feeder's data after feeding. Defaults to True.
        :return: the unique id of the scheduled feed in json

        """
        response = await self.client.api_post(
            self.api_path + "schedules", data={"time": time, "amount": amount}
        )
        response.raise_for_status()

        if update_data:
            await self.update_data()

        return json.loads(response.content.decode("UTF-8"))

    async def modify_schedule(
        self,
        time: str = "00:00",
        amount: int = 1,
        schedule_id: str = "",
        update_data: bool = True,
    ) -> None:
        """
        Modifies the specified schedule.

        :param time: the time to dispense the food in 24 hour notation with colon separation (e.g. 16:35 for 4:35PM)
        :param amount: the amount to feed in 1/8 increments.
        :param schedule_id: the id of the scheduled feed to delete (six digits as of writing)
        :param update_data: if True, will update the feeder's data after feeding. Defaults to True.

        """
        response = await self.client.api_put(
            self.api_path + "schedules/" + schedule_id,
            data={"time": time, "amount": amount},
        )
        response.raise_for_status()

        if update_data:
            await self.update_data()

    async def delete_schedule(
        self, schedule_id: str = "", update_data: bool = True
    ) -> None:
        """
        Deletes specified schedule.

        :param schedule_id: the id of the scheduled feed to delete (six digits as of writing)
        :param update_data: if True, will update the feeder's data after feeding. Defaults to True.

        """
        response = await self.client.api_delete(
            self.api_path + "schedules/" + schedule_id
        )
        response.raise_for_status()

        if update_data:
            await self.update_data()

    async def delete_all_schedules(self, update_data: bool = True) -> None:
        """
        Deletes all schedules.

        :param update_data: if True, will update the feeder's data after feeding. Defaults to True.

        """
        response = await self.client.api_delete(self.api_path + "schedules")
        response.raise_for_status()

        if update_data:
            await self.update_data()

    async def pause_schedules(self, value: bool, update_data: bool = True) -> None:
        """
        Pauses all schedules.

        :param update_data: if True, will update the feeder's data after feeding. Defaults to True.

        """
        response = await self.client.api_put(
            self.api_path + "settings/paused", data={"value": value}
        )
        response.raise_for_status()

        if update_data:
            await self.update_data()

    async def pause(self, value: bool = True) -> None:
        """
        Sets or unsets the pause feeding value
        """
        await self.put_setting("paused", value)

    async def lock(self, value: bool = True) -> None:
        """
        Sets or unsets the button lock value.
        """
        await self.put_setting("child_lock", value)

    async def slow_feed(self, value: bool = True) -> None:
        """Sets or unsets the slow feed setting."""
        await self.put_setting("slow_feed", value)

    @property
    def api_name(self) -> str:
        """The feeder's thing_name from the API."""
        return self.data["thing_name"]

    @property
    def api_path(self) -> str:
        """The feeder's path on the API."""
        return "smart-feed/feeders/" + self.api_name + "/"

    @property
    def id(self) -> str:
        """The feeder's ID."""
        return self.data["id"]

    @property
    def battery_voltage(self) -> float:
        """The feeder's calculated current battery voltage."""
        try:
            return round(int(self.data["battery_voltage"]) / 32767 * 7.2, 3)
        except ValueError:
            return -1

    @property
    def battery_level(self) -> int:
        """
        The feeder's current battery level on a scale of 0-100.
        Returns 0 if no batteries installed.

        """
        if not self.data["is_batteries_installed"]:
            return 0
        minVoltage = 22755
        maxVoltage = 29100
        return round(
            max(
                (100 * (int(self.data["battery_voltage"]) - minVoltage))
                / (maxVoltage - minVoltage),
                0,
            )
        )

    @property
    def is_paused(self) -> bool:
        """If true, the feeder will not follow its scheduling."""
        return self.data["settings"]["paused"]

    @property
    def is_slow_feed(self) -> bool:
        """If true, the feeder will dispense food slowly."""
        return self.data["settings"]["slow_feed"]

    @property
    def is_locked(self) -> bool:
        """If true, the feeder's physical button is disabled."""
        return self.data["settings"]["child_lock"]

    @property
    def friendly_name(self) -> str:
        """The feeder's display name."""
        return self.data["settings"]["friendly_name"]

    @property
    def pet_type(self) -> str:
        """The feeder's pet type."""
        return self.data["settings"]["pet_type"]

    @property
    def food_sensor_current(self) -> str:
        """The feeder's food sensor status."""
        return self.data["food_sensor_current"]

    @property
    def food_low_status(self) -> int:
        """
        The feeder's food low status.

        :return: 0 if Full, 1 if Low, 2 if Empty

        """
        return int(self.data["is_food_low"])

    @property
    def firmware(self) -> str:
        """The feeder's firmware."""
        return self.data["firmware_version"]

    @property
    def product_name(self) -> str:
        """The feeder's product name."""
        return self.data["product_name"]


class DeviceScoopfree:
    def __init__(self, client, data):
        """
        PetSafe Scoopfree device.

        :param client: PetSafeClient with authorization tokens
        :param data: data regarding litterbox
        """
        self.client = client
        self.data = data

    def __str__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        """
        All litterbox data formatted as JSON.

        """
        return json.dumps(self.data, indent=2)

    async def update_data(self) -> None:
        """
        Updates self.data to the litterbox's current online state.
        """
        response = await self.client.api_get(self.api_path)
        response.raise_for_status()
        self.data = json.loads(response.content.decode("UTF-8"))

    async def rake(self, update_data: bool = True):
        """
        Triggers the rake to begin raking.
        :param update_data: if True, will update the litterbox's data after raking. Defaults to True.
        """
        response = await self.client.api_post(self.api_path + "rake-now", data={})
        response.raise_for_status()

        if update_data:
            await self.update_data()
            return self.data["data"]

    async def reset(self, rakeCount: int = 0, update_data: bool = True):
        """
        Resets the rake count to the specified value.
        :param rakeCount: the value to set the rake count to.
        :param update_data: if True, will update the litterbox's data after feeding. Defaults to True.
        """
        response = await self.client.api_patch(
            self.api_path + "shadow",
            data={"rakeCount": rakeCount},
        )
        response.raise_for_status()

        if update_data:
            await self.update_data()
            return self.data["data"]

    async def modify_timer(self, rakeDelayTime: int = 15, update_data: bool = True):
        """
        Modifies the rake timer.
        :param rakeDelayTime: The amount of time for the rake delay in minutes.
        :param update_data: if True, will update the litterbox's data after feeding. Defaults to True.
        """
        response = await self.client.api_patch(
            self.api_path + "shadow",
            data={"rakeDelayTime": rakeDelayTime},
        )
        response.raise_for_status()

        if update_data:
            await self.update_data()
            return self.data["data"]

    async def get_activity(self):
        """
        Requests all litterbox ativity.

        :return: the APIs response in JSON.

        """
        response = await self.client.api_get(self.api_path + "activity")
        response.raise_for_status()
        return json.loads(response.content.decode("UTF-8"))

    async def patch_setting(
        self, setting: str, value, force_update: bool = False
    ) -> None:
        """
        Changes the value of a specified setting. Sends PATCH to API.

        :param setting: the setting to change
        :param value: the new value of that setting
        :param force_update: if True, update ALL data after PATCH. Defaults to False.

        """
        response = await self.client.api_patch(
            self.api_path + "settings", data={setting: value}
        )
        response.raise_for_status()

        if force_update:
            await self.update_data()
        else:
            self.data[setting] = value

    @property
    def api_name(self) -> str:
        """The litterbox's thingName from the API."""
        return self.data["thingName"]

    @property
    def api_path(self) -> str:
        """The litterbox's path on the API."""
        return "scoopfree/product/product/" + self.api_name + "/"

    @property
    def friendly_name(self) -> str:
        """The litterbox's display name."""
        return self.data["friendlyName"]

    @property
    def firmware(self) -> str:
        """The litterbox firmware."""
        return self.data["shadow"]["state"]["reported"]["firmware"]

    @property
    def product_name(self) -> str:
        """The litterbox product name."""
        return self.data["productName"]


class DeviceSmartDoor:
    """Representation of a PetSafe SmartDoor device."""

    def __init__(self, client, data: dict):
        self.client = client
        self.data = data

    @classmethod
    async def get_smartdoor(cls, client, thing_name: str) -> "DeviceSmartDoor":
        """Fetch the details for a single SmartDoor identified by ``thing_name``."""

        if not thing_name:
            raise ValueError("thing_name must be provided")

        response = await client.api_get(
            f"smartdoor/product/product/{thing_name}/"
        )
        content = response.content.decode("UTF-8")
        data = json.loads(content)
        payload = data.get("data", data)
        return cls(client, payload)

    @classmethod
    async def set_smartdoor_mode(
        cls, client, thing_name: str, mode: str, *, update_data: bool = True
    ) -> "DeviceSmartDoor":
        """Set the operating ``mode`` for the SmartDoor identified by ``thing_name``."""

        if not thing_name:
            raise ValueError("thing_name must be provided")

        door = cls(client, {"thingName": thing_name})
        await door.set_mode(mode, update_data=update_data)
        return door

    @classmethod
    async def manual_lock_smartdoor(
        cls, client, thing_name: str, *, update_data: bool = True
    ) -> "DeviceSmartDoor":
        """Lock the SmartDoor manually using the documented API."""

        return await cls.set_smartdoor_mode(
            client,
            thing_name,
            SMARTDOOR_MODE_MANUAL_LOCKED,
            update_data=update_data,
        )

    @classmethod
    async def manual_unlock_smartdoor(
        cls, client, thing_name: str, *, update_data: bool = True
    ) -> "DeviceSmartDoor":
        """Unlock the SmartDoor manually using the documented API."""

        return await cls.set_smartdoor_mode(
            client,
            thing_name,
            SMARTDOOR_MODE_MANUAL_UNLOCKED,
            update_data=update_data,
        )

    @classmethod
    async def smart_mode_smartdoor(
        cls, client, thing_name: str, *, update_data: bool = True
    ) -> "DeviceSmartDoor":
        """Enable Smart mode on the SmartDoor using the documented API."""

        return await cls.set_smartdoor_mode(
            client,
            thing_name,
            SMARTDOOR_MODE_SMART,
            update_data=update_data,
        )

    def __str__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        """Return the SmartDoor payload encoded as JSON."""

        return json.dumps(self.data, indent=2)

    async def update_data(self) -> None:
        """Refresh the SmartDoor data from the API."""

        response = await self.client.api_get(self.api_path)
        response.raise_for_status()
        payload = json.loads(response.content.decode("UTF-8"))
        self.data = payload.get("data", payload)

    async def get_preferences(self) -> dict:
        """Return the SmartDoor preference data."""

        response = await self.client.api_get(self.preferences_api_path)
        response.raise_for_status()
        payload = json.loads(response.content.decode("UTF-8"))
        data = payload.get("data", payload)
        if isinstance(data, dict):
            return self._normalize_preferences(data)
        raise ValueError("Unexpected response payload for SmartDoor preferences")

    async def update_friendly_name(
        self, friendly_name: str, *, update_data: bool = True
    ) -> dict:
        """Update the SmartDoor friendly name preference."""

        if not friendly_name:
            raise ValueError("friendly_name must be provided")
        return await self._patch_preferences(
            {"friendlyName": friendly_name}, update_data=update_data
        )

    async def update_timezone(
        self, timezone: str, *, update_data: bool = True
    ) -> dict:
        """Update the SmartDoor timezone preference."""

        if not timezone:
            raise ValueError("timezone must be provided")
        return await self._patch_preferences({"tz": timezone}, update_data=update_data)

    async def get_activity(
        self, *, limit: Optional[int] = None, since: Optional[str] = None
    ) -> list[dict]:
        """Return SmartDoor activity entries.

        :param limit: Optional maximum number of entries to return.
        :param since: Optional ISO timestamp filter understood by the API.
        """

        path = self.api_path + "activity"
        query: list[str] = []
        if limit is not None:
            limit_value = int(limit)
            if limit_value <= 0:
                raise ValueError("limit must be a positive integer")
            query.append(f"limit={limit_value}")
        if since is not None:
            from urllib.parse import quote_plus

            query.append(f"since={quote_plus(since)}")
        if query:
            path += "?" + "&".join(query)

        response = await self.client.api_get(path)
        response.raise_for_status()
        payload = json.loads(response.content.decode("UTF-8"))
        data = payload.get("data", payload)
        if isinstance(data, list):
            return data
        if data is None:
            return []
        return [data]

    async def set_mode(self, mode: str, update_data: bool = True) -> None:
        """Set the SmartDoor operating mode.

        Valid modes include :data:`petsafe.const.SMARTDOOR_MODE_MANUAL_LOCKED`,
        :data:`petsafe.const.SMARTDOOR_MODE_MANUAL_UNLOCKED`, and
        :data:`petsafe.const.SMARTDOOR_MODE_SMART`.
        """

        await self.client.api_patch(
            self.api_path + "shadow", data={"door": {"mode": mode}}
        )

        if update_data:
            await self.update_data()
        else:
            door_state = self._ensure_door_state()
            door_state["mode"] = mode

    async def lock(self, update_data: bool = True) -> None:
        """Lock the SmartDoor manually."""

        await self.set_mode(
            SMARTDOOR_MODE_MANUAL_LOCKED, update_data=update_data
        )

    async def unlock(self, update_data: bool = True) -> None:
        """Unlock the SmartDoor manually."""

        await self.set_mode(
            SMARTDOOR_MODE_MANUAL_UNLOCKED, update_data=update_data
        )

    async def smart_mode(self, update_data: bool = True) -> None:
        """Enable Smart mode on the SmartDoor."""

        await self.set_mode(SMARTDOOR_MODE_SMART, update_data=update_data)

    async def set_final_act(self, final_act: str, update_data: bool = True) -> None:
        """Set the SmartDoor final act state when power is lost."""

        if final_act not in {
            SMARTDOOR_FINAL_ACT_LOCKED,
            SMARTDOOR_FINAL_ACT_UNLOCKED,
        }:
            raise ValueError("Unsupported final_act value")

        await self.client.api_patch(
            self.api_path + "shadow", data={"power": {"finalAct": final_act}}
        )

        if update_data:
            await self.update_data()
        else:
            power_state = self._ensure_power_state()
            power_state["finalAct"] = final_act

    async def set_final_act_locked(self, update_data: bool = True) -> None:
        """Configure the SmartDoor to lock when power is lost."""

        await self.set_final_act(SMARTDOOR_FINAL_ACT_LOCKED, update_data=update_data)

    async def set_final_act_unlocked(self, update_data: bool = True) -> None:
        """Configure the SmartDoor to unlock when power is lost."""

        await self.set_final_act(SMARTDOOR_FINAL_ACT_UNLOCKED, update_data=update_data)

    async def get_schedules(self, *, update_data: bool = False) -> list[dict]:
        """Return the SmartDoor schedules configured for this device."""

        response = await self.client.api_get(
            f"smartdoor/product/schedules?thingName={self.api_name}"
        )
        response.raise_for_status()
        payload = json.loads(response.content.decode("UTF-8"))
        data = payload.get("data", payload)
        schedules = data if isinstance(data, list) else []
        if update_data:
            self.data["schedules"] = schedules
        return schedules

    async def get_override_schedules(self) -> list[dict]:
        """Return override schedules configured for the SmartDoor."""

        response = await self.client.api_get(
            f"smartdoor/product/override/schedules/{self.api_name}"
        )
        response.raise_for_status()
        payload = json.loads(response.content.decode("UTF-8"))
        data = payload.get("data", payload)
        if data is None:
            return []
        if isinstance(data, list):
            return data
        return [data]

    async def override_schedule(
        self, access: int, *, update_data: bool = True
    ) -> dict:
        """Apply a temporary override schedule to the SmartDoor."""

        response = await self.client.api_patch(
            "smartdoor/product/override/schedules",
            data={"thingName": self.api_name, "access": int(access)},
        )
        response.raise_for_status()
        payload = json.loads(response.content.decode("UTF-8"))
        data = payload.get("data", payload)
        if update_data:
            await self.update_data()
        return data

    async def save_schedule(
        self, schedule: dict, *, update_data: bool = True
    ) -> dict:
        """Create or update a SmartDoor schedule."""

        if not isinstance(schedule, dict):
            raise TypeError("schedule must be a dict")
        payload = dict(schedule)
        payload.setdefault("thingName", self.api_name)
        response = await self.client.api_post(
            "smartdoor/product/schedules", data=payload
        )
        response.raise_for_status()
        response_payload = json.loads(response.content.decode("UTF-8"))
        data = response_payload.get("data", response_payload)
        if update_data:
            await self.update_data()
        return data

    async def delete_schedule(
        self, schedule_id: str, *, update_data: bool = True
    ) -> None:
        """Delete a SmartDoor schedule by identifier."""

        if not schedule_id:
            raise ValueError("schedule_id must be provided")
        await self.client.api_delete(
            f"smartdoor/product/schedules/{schedule_id}"
        )
        if update_data:
            await self.update_data()

    @property
    def api_name(self) -> str:
        """Return the SmartDoor thing name used by the API."""

        name = self.data.get("thingName") or self.data.get("thing_name")
        if not name:
            raise KeyError("SmartDoor thing name not found in data")
        return name

    @property
    def api_path(self) -> str:
        """Return the API path for the SmartDoor."""

        return f"smartdoor/product/product/{self.api_name}/"

    @property
    def preferences_api_path(self) -> str:
        """Return the API path for SmartDoor preferences."""

        return f"preferences/product/smartdoor/{self.api_name}"

    @property
    def schedules(self) -> list[dict]:
        """Return the configured SmartDoor schedules."""

        return self.data.get("schedules", [])

    @property
    def friendly_name(self) -> Optional[str]:
        """Return the SmartDoor friendly name preference."""

        return self.data.get("friendlyName")

    @property
    def timezone(self) -> Optional[str]:
        """Return the SmartDoor timezone preference."""

        return self.data.get("tz")

    @property
    def mode(self) -> Optional[str]:
        """Return the currently reported operating mode."""

        return self._reported_door_state().get("mode")

    @property
    def latch_state(self) -> Optional[str]:
        """Return the latch state of the SmartDoor."""

        return self._reported_door_state().get("latchState")

    @property
    def error_state(self) -> Optional[str]:
        """Return the SmartDoor error state, if any."""

        return self._reported_door_state().get("errorState")

    @property
    def battery_level(self) -> Optional[int]:
        """Return the SmartDoor battery percentage."""

        return self._reported_power_state().get("batteryLevel")

    @property
    def battery_voltage(self) -> Optional[int]:
        """Return the SmartDoor battery voltage."""

        return self._reported_power_state().get("batteryVoltage")

    @property
    def has_adapter(self) -> Optional[bool]:
        """Return whether the SmartDoor is on AC power."""

        return self._reported_power_state().get("hasAdapter")

    @property
    def firmware(self) -> Optional[str]:
        """Return the firmware version reported by the SmartDoor."""

        return self._reported_system_status().get("firmware")

    @property
    def rssi(self) -> Optional[int]:
        """Return the Wi-Fi RSSI reported by the SmartDoor."""

        return self._reported_system_status().get("rssi")

    @property
    def connection_status(self) -> Optional[str]:
        """Return the SmartDoor connection status."""

        return self._reported_state().get("connectionStatus")

    def _reported_state(self) -> dict:
        return (
            self.data.get("shadow", {})
            .get("state", {})
            .get("reported", {})
        )

    def _reported_door_state(self) -> dict:
        return self._reported_state().get("door", {})

    def _reported_power_state(self) -> dict:
        return self._reported_state().get("power", {})

    def _reported_system_status(self) -> dict:
        return self._reported_state().get("systemStatus", {})

    def _ensure_door_state(self) -> dict:
        shadow = self.data.setdefault("shadow", {})
        state = shadow.setdefault("state", {})
        reported = state.setdefault("reported", {})
        return reported.setdefault("door", {})

    def _ensure_power_state(self) -> dict:
        shadow = self.data.setdefault("shadow", {})
        state = shadow.setdefault("state", {})
        reported = state.setdefault("reported", {})
        return reported.setdefault("power", {})

    async def _patch_preferences(
        self, preferences: dict, *, update_data: bool
    ) -> dict:
        response = await self.client.api_patch(
            self.preferences_api_path, data=preferences
        )
        response.raise_for_status()
        if update_data:
            await self.update_data()
        if not response.content:
            return {}
        payload = json.loads(response.content.decode("UTF-8"))
        data = payload.get("data", payload)
        if isinstance(data, dict):
            return self._normalize_preferences(data)
        raise ValueError("Unexpected response payload for SmartDoor preferences")

    @staticmethod
    def _normalize_preferences(data: dict) -> dict:
        """Flatten preference data returned by the SmartDoor API."""

        normalized = dict(data)
        preference_data = normalized.pop("preferenceData", None)
        if isinstance(preference_data, dict):
            normalized.update(preference_data)
        return normalized
