import base64
import csv
import json
import os
import re
import tempfile
import zipfile
from io import TextIOWrapper
from pathlib import Path
from typing import Iterator, Optional

import requests
from langchain_core.documents import Document

from langchain_community.document_loaders.base import BaseLoader


class KyvosLoader(BaseLoader):
    """Load the Kyvos Semantic model data into List of Documents.
        Each document represents one record from semantic model. 
        Every row is converted into a key/value pair in case of fetched 
        data is of csv type. In case of json first document is by defualt
        schema of the table as a document object. Data is fetched from kyvos
        semantic model by hitting Rest endpoints and data is temporary stored 
        in local box either in csv or in json format specified by the user.
        Once the file is used by loader then file is auto removed from the local 
        box.

     Args:
        configuration_parameters:configuration parameters needed to hit the rest 
        endpoints.
        username: username to be logged in
        password: password to be logged in
        query: query to execute on semantic model
        jwt_token: jwt token to logged in
        schema: jq expression for json files

    Note:
        Either username with password is needed or either
        jwt token is needed for validation purpose
    """

    def __init__(
        self,
        configuration_parameters: dict,
        username: Optional[str] = None,
        password: Optional[str] = None,
        query: str = None,
        jwt_token: str = None,
        schema: str = ".metadata, .rows[]",
    ):
        #### Initialization parameters for Rest End Points ####

        self.__dict__ = configuration_parameters
        self.jwt_token = os.getenv("KYVOS_Token") or jwt_token

        if self.jwt_token is None:
            self.username = os.getenv("KYVOS_USERNAME") or username
            if self.username is None:
                raise ValueError(
                    """Got Null value for username. 
                       Either pass the username or 
                       set the value in enviornment variable by 'KYVOS_USERNAME' """
                )
            self.password = os.getenv("KYVOS_PASSWORD") or password
            if self.password is None:
                raise ValueError(
                    """Got Null value for password. 
                     Either pass the password or 
                     set the value in enviornment variable by 'KYVOS_PASSWORD'"""
                )
        else:
            self.username = None
            self.password = None

        self.query = query
        self.schema = schema

    def get_headers(self) -> str:
        """Return the header depending on whether user want to hit the 
           rest endpoints by session_id, basic token or jwt token"""
        ## Based on Session id which require login_url in configuration parameters ##
        headers = {
            "Accept": "",
            "Content-Type": "",
            "Authorization": "",
            "sessionid": "",
        }
        import xml.etree.ElementTree
        self.ET=xml.etree.ElementTree
        if self.__dict__.get("login_url", None) is not None:
            try:
                conn_headers = {
                    "Accept": "application/XML",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                conn_body = {
                    "username": f"{self.username}",
                    "password": f"{self.password}",
                }

                response = requests.post(
                    url=self.login_url,
                    headers=conn_headers,
                    data=conn_body,
                )
                response.raise_for_status()
                
                root = self.ET.fromstring(response.text)

                session_id = root.find("SUCCESS").text

                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": self.header_accept,
                    "sessionid": f"{session_id}",
                }
            except Exception as e:
                raise RuntimeError(f"An error occurred: {e}")
                

        #### Based on JWT Token ####
        elif self.jwt_token:
            oauth_token = "oauth " + self.jwt_token
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": self.header_accept,
                "Authorization": f"{oauth_token}",
                "appType": "PUBLIC",
            }

        ### Based on Basic Token #####
        else:
            usrPass = f"{self.username}:{self.password}"
            usrPass_bytes = usrPass.encode("ascii")
            base64_bytes = base64.b64encode(usrPass_bytes)
            base64_string = base64_bytes.decode("ascii")
            basic_auth = "Basic " + base64_string

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": self.header_accept,
                "Authorization": f"{basic_auth}",
            }
     
        return headers

    def lazy_load(self):
        """In this function first we save the data temporary onto the local box
           depending on user specification, then we lazily load the file to give
           a document iterator.
        """

        #### Setting Parameters for application/octet-stream ####
        if self.header_accept == "application/octet-stream":
            if self.output_format == "csv":
                if self.zipped == "false":
                    self.file_path = "temp.csv"
                else:
                    self.file_path = "temp.zip"
            elif self.output_format == "json":
                import jq
                self.jq = jq
                if self.zipped == "false":
                    self.file_path = "temp.json"
                else:
                    self.file_path = "temp.zip"
                    
        #### Setting Parameters for application/json ####
        elif self.header_accept == "application/json":
            self.zipped = "false"
            self.output_format = "json"
            import jq
            self.jq = jq
            self.file_path = "temp.json"
            if ".csv" in self.output_file_name:
                self.output_file_name = re.sub(".csv", ".json", self.output_file_name)

        ### Setting Parameters for temporary saving the files #######
        self.temp_dir = tempfile.TemporaryDirectory()
        _, suffix = os.path.splitext(self.file_path)
        temp_file = os.path.join(self.temp_dir.name, f"tmp{suffix}")
        self.file_path = str(temp_file)

        ### Getting the headers and sending a post request to get data ####
        headers = self.get_headers()
        payload = f"queryType={self.query_type}"+ \
                       f"&query={self.query}"+ \
                       f"&lineSeparator={self.line_seperator}"+ \
                       f"&enclosedBy={self.enclosed_by}"+ \
                       f"&zipped={self.zipped}"+ \
                       f"&includeHeader={self.include_header}"+ \
                       f"&keepMeasureFormatting={self.kms}"+ \
                       f"&outputFormat={self.output_format}"+ \
                       f"&maxRows={self.maxRows}"
     

        try:
            ##### Saving the data on hard-disk using chunking ######
            try:
                with requests.post(
                    self.query_url, stream=True, data=payload, headers=headers
                ) as response:
                    response.raise_for_status()
                    with open(self.file_path, "wb") as f:
                        for chunk in response.iter_content():
                            f.write(chunk)
            except requests.exceptions.HTTPError as e:
                raise RuntimeError(f"Request failed with status code {e.response.status_code}")
               

            ##### Extracting the zipfile ######
            if self.zipped == "true":
                with zipfile.ZipFile(self.file_path) as z:
                    z.extractall(self.temp_dir.name)
                    self.file_path = [
                        file
                        for file in os.listdir(self.temp_dir.name)
                        if file.endswith(".csv") or file.endswith(".json")
                    ][0]
                    self.file_path = os.path.join(self.temp_dir.name, self.file_path)

            ##### csv Data Parsing ######
            if self.output_format == "csv":
                try:
                    with open(self.file_path, newline="") as file:
                        yield from self._kyvos_csv_parser(file)
                except FileNotFoundError as e:
                    raise FileNotFoundError(f"File not found: {e}")
                except Exception as e:
                    raise RuntimeError(f"An error occurred: {e}")

            #### Json data parsing ######
            elif self.output_format == "json":
                try:
                    self.file_path = Path(self.file_path).resolve()
                    self.schema = self.jq.compile(self.schema)
                    counter = 0
                    with open(self.file_path, "r", encoding="utf-8") as file:
                        for doc in self._kyvos_json_parser(file.read(), counter):
                            yield doc
                            counter += 1

                except FileNotFoundError as e:
                    raise FileNotFoundError(f"File not found: {e}")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Json Decoding error {e}")

        except Exception as e:
            raise RuntimeError(f"An error occurred: {e}")

    ##### Functions to be used for json parsing #####

    def _kyvos_json_parser(self, raw_text: str, counter: int) -> Iterator[Document]:
        kyvos_data = self.schema.input(json.loads(raw_text))
        for i, text in enumerate(kyvos_data, counter + 1):
            metadata = {"file_name": str(self.output_file_name), "row_no": i}
            yield Document(page_content=str(text), metadata=metadata)

    #### Functions to be used for csv parsing  ####
    def _kyvos_csv_parser(self, file: TextIOWrapper) -> Iterator[Document]:
        kyvos_csv_reader = csv.DictReader(file)
        for i, row in enumerate(kyvos_csv_reader):
            data_list = []
            for k, v in row.items():
                value = v if v is not None else ""
                data_list.append(f"{k}: {value}")
            data = ",".join(data_list)
            metadata = {"file_name": self.output_file_name, "row_no": i}
            yield Document(page_content=data, metadata=metadata)

    ## Magic Method to auto delete the file ####
    def __del__(self) -> None:
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()
