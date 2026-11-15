import unittest #built-in python testing framework
from unittest.mock import patch
from src.askwestern.ingest import scrape

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

class TestRegistrarScraper(unittest.TestCase):
    #mock the functions from the actual scrape.py
    @patch("src.askwestern.ingest.scrape.check_robots")
    @patch("src.askwestern.ingest.scrape.requests.get")
    def test_blocked_page(self, mock_get, mock_robots):
        #simulate scraping permission denied
        mock_robots.return_value = False

        #create simple registrar source
        source = {
            "source_id": "REG001",
            "url": "https://registrar.uwo.ca/example.html"
        }

        #run download function
        result = scrape.download_page(source)

        #verify that downloading was unsuccessful
        self.assertFalse(result)

        #verify no webpage request was made
        mock_get.assert_not_called()

    @patch("src.askwestern.ingest.scrape.check_robots")
    @patch("src.askwestern.ingest.scrape.requests.get")
    @patch("src.askwestern.ingest.scrape.time.sleep")   #skip the delay just for the testing
    def test_successful_download(self, mock_sleep, mock_get, mock_robots): 
        #simulate approved scraping permissions
        mock_robots.return_value = True   

        #create fake HTTP response
        fake_response = Mock()
        fake_response.status_code = 200
        fake_response.headers = {"Content-Type": "text/html"}
        fake_response.content = b"<html><body>Registrar Test Page</body></html>"

        mock_get.return_value = fake_response #replace real req with fake res

        #create a sample sourced
        source = {
            "source_id": "REG001",
            "url": "https://registrar.uwo.ca/example.html",
            "notes": "Test Registrar Page"
        }

        #use temp dict for output
        with TemporaryDirectory() as temp_dir:
            with patch.object(scrape, "output_dir", Path(temp_dir)):
                #run the douwload
                result = scrape.download_page(source)

                #check the success of download
                self.assertTrue(result)

                #check html was created
                html_file = Path(temp_dir) / "REG001.html"
                self.assertTrue(html_file.exists())

                #check metadat file exists and read it
                metadata_file = Path(temp_dir) / "REG001.json"
                self.assertTrue(metadata_file.exists())
                metadata = json.loads(metadata_file.read_text(encoding = "utf-8"))

                #verify metadata
                self.assertEqual(metadata["source_id"], "REG001")
                self.assertEqual(metadata["source_type"], "html")


            #verify one webpage req was made
            mock_get.assert_called_once()    


    #testing how the scraper handles redirects
    @patch("src.askwestern.ingest.scrape.check_robots")
    @patch("src.askwestern.ingest.scrape.requests.get")
    @patch("src.askwestern.ingest.scrape.time.sleep")
    def test_redirect(self, mock_sleep, mock_get, mock_robots):
        #simulate approved permissions
        mock_robots.return_value = True

        #simulate redirect response
        fake_response = Mock()
        fake_response.status_code = 302
        mock_get.return_value = fake_response

        #sample source
        source = {
            "source_id": "REG001",
            "url": "https://registrar.uwo.ca/example.html"
        }

        result = scrape.download_page(source)

        #verify the redirect was skipped
        self.assertFalse(result)

        #verify that only one request was attempted
        mock_get.assert_called_once()


    #test http errors 
    @patch("src.askwestern.ingest.scrape.check_robots")
    @patch("src.askwestern.ingest.scrape.requests.get")
    @patch("src.askwestern.ingest.scrape.time.sleep")
    def test_http_error(self, mock_sleep, mock_get, mock_robots):
        #simulate approved permission
        mock_robots.return_value = True

        #simulate failed hhtp request
        fake_response = Mock()
        fake_response.status_code = 404

        #allows us to choose what happens when mocked function is called
        fake_response.raise_for_status.side_effect = scrape.requests.HTTPError("404 Not Found")


        mock_get.return_value = fake_response

        #sample source
        source = {
            "source_id": "REG001",
            "url": "https://registrar.uwo.ca/example.html"
        }

        #run the download function
        result = scrape.download_page(source)
        self.assertFalse(result)
        mock_get.assert_called_once()


    #testing unexpected content types (ex: pdf)
    @patch("src.askwestern.ingest.scrape.check_robots")
    @patch("src.askwestern.ingest.scrape.requests.get")
    @patch("src.askwestern.ingest.scrape.time.sleep")  
    def test_content_type(self, mock_sleep, mock_get, mock_robots):
        mock_robots.return_value = True
        fake_response = Mock()
        fake_response.status_code = 200
        fake_response.headers = {"Content-Type": "application/pdf"}

        mock_get.return_value = fake_response
        source = {
            "source_id": "REG001",
            "url": "https://registrar.uwo.ca/example.pdf"
        }

        #use temp dict 
        with TemporaryDirectory() as temp_dir:
            with patch.object(scrape, "output_dir", Path(temp_dir)):
                result = scrape.download_page(source)
                self.assertFalse(result)
                html_file = Path(temp_dir) / "REG001.html"
                self.assertFalse(html_file.exists())

                #verify metadata was saved
                metadata_file = Path(temp_dir) / "REG001.json"
                self.assertFalse(metadata_file.exists())

        mock_get.assert_called_once()        

    #testing the download of pages with missing robots.txt files
    @patch("src.askwestern.ingest.scrape.requests.get")
    def test_missing_robots(self, mock_get):
        #simulate page without robots.txt
        fake_response = Mock()
        fake_response.status_code = 302
        fake_response.headers = {
            "Location": "https://registrar.uwo.ca/404.html"
        }

        mock_get.return_value = fake_response

        #sample registrar page
        url = "https://registrar.uwo.ca/example.html"

        allowed = scrape.check_robots(url)
        self.assertTrue(allowed)
        mock_get.assert_called_once()
        

