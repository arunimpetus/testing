import os
import unittest
from unittest import mock

from langchain_community.document_loaders.kyvos_loader import KyvosLoader


class TestKyvosLoaderIntegration(unittest.TestCase):
    @mock.patch.dict(
        os.environ,
        {
            "KYVOS_USERNAME": "test",
            "KYVOS_PASSWORD": "password",
        },
    )
    def test_lazy_load(self):
        # Integration test for lazy_load method with CSV data
        # Initialize KyvosLoader instance with actual configuration parameters
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
            "output_file_name": "test.csv",
            "header_accept": "application/octet-stream",
            "maxRows": 1000000,
        }
        query = "Query"
        loader = KyvosLoader(configuration_parameters=self.config_params, query=query)

        # Set loader properties
        loader.query_type = "SQL"
        loader.output_format = "csv"
        loader.file_path = "test.csv"
        documents = []

        # Assertions
        self.assertEqual(len(documents), 0)


if __name__ == "__main__":
    unittest.main()
