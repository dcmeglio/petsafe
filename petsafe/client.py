import json
import re
import time

from botocore.config import Config
from botocore.session import Session, get_session
from botocore import UNSIGNED
import asyncio
import httpx

from petsafe.devices import DeviceScoopfree, DeviceSmartFeed

from .const import PETSAFE_API_BASE, PETSAFE_CLIENT_ID, PETSAFE_REGION


class PetSafeClient:
    def __init__(
        self,
        email: str,
        id_token: str = None,
        refresh_token: str = None,
        access_token: str = None,
        session: str = None,
        client: httpx.AsyncClient = None,
    ):
        self._id_token = id_token
        self._refresh_token = refresh_token
        self._access_token = access_token
        self._email = email
        self._session = session
        self._username = None
        self._token_expires_time = 0
        self._challenge_name = None
        if client is not None:
            self._client = client
        else:
            self._client = httpx.AsyncClient()
        self._cognitoSession = None
        self._cognitoClient = None

    async def get_feeders(self) -> list[DeviceSmartFeed]:
        """
        Sends a request to PetSafe's API for all feeders associated with account.

        :param client: PetSafeClient with authorization tokens
        :return: list of Feeders

        """
        response = await self.api_get("smart-feed/feeders")
        content = response.content.decode("UTF-8")
        return [
            DeviceSmartFeed(self, feeder_data) for feeder_data in json.loads(content)
        ]

    async def get_litterboxes(self) -> list[DeviceScoopfree]:
        """
        Sends a request to PetSafe's API for all litterboxes associated with account.

        :param client: PetSafeClient with authorization tokens
        :return: list of Scoopfree litterboxes

        """
        response = await self.api_get("scoopfree/product/product")
        content = response.content.decode("UTF-8")
        return [
            DeviceScoopfree(self, litterbox_data)
            for litterbox_data in json.loads(content)["data"]
        ]

    async def request_code(self) -> None:
        """
        Requests an email code from PetSafe authentication.

        :return: response from PetSafe

        """
        await self.__get_cognito_session()
        idp = await self.__get_cognito_client()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: 
                idp.initiate_auth(
                    AuthFlow="CUSTOM_AUTH",
                    ClientId=PETSAFE_CLIENT_ID,
                    AuthParameters={
                        "USERNAME": self._email,
                        "AuthFlow": "CUSTOM_CHALLENGE",
                    },
                )
            )
            self._challenge_name = response["ChallengeName"]
            self._session = response["Session"]
            self._username = response["ChallengeParameters"]["USERNAME"]
            return response
        except idp.exceptions.UserNotFoundException as ex:
            raise InvalidUserException() from ex

    async def request_tokens_from_code(self, code: str) -> None:
        """
        Requests tokens from PetSafe API using emailed code.

        :param code: email code
        :return: response from PetSafe

        """
        await self.__get_cognito_session()
        idp = await self.__get_cognito_client()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: 
            idp.respond_to_auth_challenge(
                ClientId=PETSAFE_CLIENT_ID,
                ChallengeName=self._challenge_name,
                Session=self._session,
                ChallengeResponses={
                    "ANSWER": re.sub(r"\D", "", code),
                    "USERNAME": self._username,
                },
            )
        )
        if not "AuthenticationResult" in response:
            raise InvalidCodeException("Invalid confirmation code")
        self._id_token = response["AuthenticationResult"]["IdToken"]
        self._access_token = response["AuthenticationResult"]["AccessToken"]
        self._refresh_token = response["AuthenticationResult"]["RefreshToken"]
        self._token_expires_time = (
            time.time() + response["AuthenticationResult"]["ExpiresIn"]
        )

    async def __get_cognito_session(self) -> Session:
        """
        Retrieve a cognito session from botocore.

        :return: botocore session
        """
        if self._cognitoSession is None:
            loop = asyncio.get_event_loop()
            self._cognitoSession = await loop.run_in_executor(None, get_session)
        return self._cognitoSession
    
    async def __get_cognito_client(self):
        """
        Retrieve a cognito client.

        :return: cognito client
        """
        if self._cognitoClient is None:
            loop = asyncio.get_event_loop()
            self._cognitoClient = await loop.run_in_executor(None, lambda session:
                session.create_client(
                    "cognito-idp",
                    region_name=PETSAFE_REGION,
                    config=Config(signature_version=UNSIGNED),
                )
        , self._cognitoSession)
        return self._cognitoClient

    async def __refresh_tokens(self) -> None:
        """
        Refreshes tokens with PetSafe.

        :return: the response from PetSafe.

        """
        await self.__get_cognito_session()
        idp = await self.__get_cognito_client()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda:
            idp.initiate_auth(
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={"REFRESH_TOKEN": self._refresh_token},
                ClientId=PETSAFE_CLIENT_ID,
            )
        )

        if "Session" in response:
            self._session = response["Session"]

        self._id_token = response["AuthenticationResult"]["IdToken"]
        self._access_token = response["AuthenticationResult"]["AccessToken"]
        if "RefreshToken" in response["AuthenticationResult"]:
            self._refresh_token = response["AuthenticationResult"]["RefreshToken"]
        self.token_expires_time = (
            time.time() + response["AuthenticationResult"]["ExpiresIn"]
        )

    async def api_post(self, path: str = "", data: dict = None):
        """
        Sends a POST to PetSafe API.

        Example: api_post(path=feeder.api_path + 'meals', data=food_data)

        :param path: the path on the API
        :param data: the POST data
        :return: the request response

        """
        headers = await self.__get_headers()
        response = await self._client.post(
            PETSAFE_API_BASE + path, headers=headers, json=data
        )
        if response.status_code == 403:
            await self.__refresh_tokens()
            response = await self._client.post(
                PETSAFE_API_BASE + path, headers=headers, json=data
            )
        response.raise_for_status()
        return response

    async def api_get(self, path: str = ""):
        """
        Sends a GET to PetSafe API.

        Example: api_get(path='feeders')

        :param path: the path on the API
        :return: the request response

        """
        headers = await self.__get_headers()
        response = await self._client.get(PETSAFE_API_BASE + path, headers=headers)
        if response.status_code == 403:
            await self.__refresh_tokens()
            response = await self._client.get(PETSAFE_API_BASE + path, headers=headers)
        response.raise_for_status()
        return response

    async def api_put(self, path: str = "", data: dict = None):
        """
        Sends a PUT to PetSafe API.

        Example: api_put(path='feeders', data=my_data)

        :param path: the path on the API
        :param data: the PUT data
        :return: the request response

        """
        headers = await self.__get_headers()
        response = await self._client.put(PETSAFE_API_BASE + path, headers=headers, json=data)
        if response.status_code == 403:
            await self.__refresh_tokens()
            response = await self._client.put(PETSAFE_API_BASE + path, headers=headers, json=data)
        response.raise_for_status()
        return response

    async def api_patch(self, path: str = "", data: dict = None):
        """
        Sends a PATCH to PetSafe API.

        Example: api_patch(path='feeders', data=my_data)

        :param path: the path on the API
        :param data: the PATCH data
        :return: the request response

        """
        headers = await self.__get_headers()
        response = await self._client.patch(
            PETSAFE_API_BASE + path, headers=headers, json=data
        )        
        if response.status_code == 403:
            await self.__refresh_tokens()
            response = await self._client.patch(
                PETSAFE_API_BASE + path, headers=headers, json=data
            )
        response.raise_for_status()
        return response

    async def api_delete(self, path: str = ""):
        """
        Sends a DELETE to PetSafe API.

        Example: api_delete(path='feeders')

        :param path: the path on the API
        :param data: the PATCH data
        :return: the request response

        """
        headers = await self.__get_headers()
        response = await self._client.delete(PETSAFE_API_BASE + path, headers=headers)
        if response.status_code == 403:
            await self.__refresh_tokens()
            response = await self._client.delete(PETSAFE_API_BASE + path, headers=headers)
        response.raise_for_status()
        return response

    async def __get_headers(self) -> dict:
        """
        Creates a dict of headers with JSON content-type and token.

        :return: dictionary of headers

        """
        headers = {"Content-Type": "application/json"}

        if self._id_token is None:
            raise Exception("Not authorized! Have you requested a token?")

        if time.time() >= self._token_expires_time - 100:
            await self.__refresh_tokens()

        headers["Authorization"] = self._id_token

        return headers

    @property
    def id_token(self) -> str:
        """Retrieve the id token associated with the connection."""
        return self._id_token

    @property
    def access_token(self) -> str:
        """Retrieve the access token associated with the connection."""
        return self._access_token

    @property
    def refresh_token(self) -> str:
        """Retrieve the refresh token associated with the connection."""
        return self._refresh_token


class InvalidCodeException(Exception):
    pass


class InvalidUserException(Exception):
    pass
