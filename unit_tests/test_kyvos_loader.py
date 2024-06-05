import os
import unittest
from unittest import mock
from unittest.mock import patch

from langchain_community.document_loaders.kyvos_loader import KyvosLoader


class TestKyvosLoader(unittest.TestCase):
    @mock.patch.dict(
        os.environ,
        {
            "KYVOS_USERNAME": "test",
            "KYVOS_PASSWORD": "password",
        },
    )
    def setUp(self):
        # Initialize necessary parameters or mock dependencies if any
        self.config_params = {
            "login_url": "https://example.com/login",
            "query_url": "https://example.com/query",
            "query_type": "SQL",
            "output_format": "csv",
            "line_seperator": "%5Cr%5Cn",
            "enclosed_by": "'",
            "connector_type": "Rest",
            "zipped": "false",
            "include_header": "true",
            "kms": "false",
            "output_file_name": "sample_data_1.csv",
            "header_accept": "application/octet-stream",
            "maxRows": 1000000,
        }
        query = "Query"
        self.loader = KyvosLoader(
            configuration_parameters=self.config_params, query=query
        )

    @patch("langchain_community.document_loaders.kyvos_loader.requests.post")
    def test_get_headers_with_login_url(self, mock_post):
        # Mocking requests.post to simulate successful response
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = b"<SUCCESS>session_id</SUCCESS>"
        self.loader.login_url = None
        self.loader.jwt_token = None
        headers = self.loader.get_headers()
        self.assertIn("Content-Type", headers)
        self.assertIn("Accept", headers)

    @patch("langchain_community.document_loaders.kyvos_loader.requests.post")
    def test_get_headers_with_jwt_token(self, mock_post):
        # Mocking requests.post to simulate successful response
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = b"<SUCCESS>session_id</SUCCESS>"
        self.loader.jwt_token = "dummy_token"
        self.loader.login_url = None
        self.loader.jwt_token = None
        headers = self.loader.get_headers()
        self.assertIn("Authorization", headers)

    @patch("langchain_community.document_loaders.kyvos_loader.requests.post")
    def test_get_headers_without_login_url_nor_jwt_token(self, mock_post):
        # Mocking requests.post to simulate successful response
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = b"<SUCCESS>session_id</SUCCESS>"
        self.loader.login_url = None
        self.loader.jwt_token = None
        headers = self.loader.get_headers()
        self.assertIn("Authorization", headers)


if __name__ == "__main__":
    unittest.main()
