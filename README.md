# gcs-checksum-api
# README

# NOTE the json format is currently incorrect for the test and must be adjusted

## Overview

a fastapi with three endpoints to generate, retrieve, and compare MD5 checksums for files stored in google cloud storage

## Installation

1. clone the repository.
2. create a virtual environment (optional but recommended)
3. install the dependencies:
   ```bash
   pip install -r requirements.txt
    ```
4. set ```GOOGLE_APPLICATION_CREDENTIALS```:
    ```
    export GOOGLE_APPLICATION_CREDENTIALS="path/to/service_account_key.json
    ```
## running the application

use the following command to run the server locally:

```uvicorn hash_validator:app --host 0.0.0.0 --port 8000```

Endpoints

1. generate checksums:

    endpoint: /generate-checksums
    method: POST

    request body:
    ```json
    {
    "source_gcs_uri": "gs://<YOUR_BUCKET>/<OPTIONAL_PATH_PREFIX>",
    "destination_bucket": "<DESTINATION_BUCKET>",
    "output_file_name": "<OUTPUT_CSV_FILE_NAME>"
    }
    ```
    description:
    generates md5 checksums for all objects under source_gcs_uri. results are saved in a csv file (filename, checksum) in the destination_bucket with the specified output_file_name

    sample response:
    ```json
    {
    "message": "Checksum file created successfully."
    }
    ```
2. compare checksums

    endpoint: /compare-checksums

    method: POST

    request Body:
    ```
    {
    "first_checksums": [
        {
        "filename": "fileA.fastq",
        "checksum": "d41d8cd98f00b204e9800998ecf8427e"
        },
        {
        "filename": "fileB.fastq",
        "checksum": "0cc175b9c0f1b6a831c399e269772661"
        }
    ],
    "second_checksums": [
        {
        "filename": "fileA.fastq",
        "checksum": "d41d8cd98f00b204e9800998ecf8427e"
        },
        {
        "filename": "fileC.fastq",
        "checksum": "900150983cd24fb0d6963f7d28e17f72"
        }
    ]
    }
    ```
    description:
    Compares two sets of filename/checksum pairs and returns matching, mismatching, and unique filenames in each set.

    sample response:
    ```
    {
    "matching": ["fileA.fastq"],
    "mismatching": [],
    "only_in_first": ["fileB.fastq"],
    "only_in_second": ["fileC.fastq"]
    }
    ```
3. get checksums

    endpoint: /get-checksums

    method: POST

    request body:
    ```
    {
    "checksum_bucket": "<BUCKET_NAME>",
    "checksum_file": "<CHECKSUM_FILE_NAME>"
    }
    ```
    description:
    retrieves a CSV file with filename, checksum from Google Cloud Storage and returns its contents as JSON.

    sample response:
    ```
    {
    "checksums": [
        {
        "filename": "fileA.fastq",
        "checksum": "d41d8cd98f00b204e9800998ecf8427e"
        },
        {
        "filename": "fileB.fastq",
        "checksum": "0cc175b9c0f1b6a831c399e269772661"
        }
    ]
    }
    ```
## testing 

A basic test script is included. You can run it after starting the FastAPI server. Note that the JSON format in test_compare_checksums must align with the API’s CompareChecksumsRequest, which expects the keys first_checksums and second_checksums. For example:
```python
def test_compare_checksums(json1, json2):
    payload = {
        "first_checksums": json1,
        "second_checksums": json2
    }
    url = "http://127.0.0.1:8000/compare-checksums"
    response = requests.post(url, json=payload)
    print("Status Code:", response.status_code)
    print("Compare Checksums Raw Response:", response.text)
    ...
```

If your JSON inputs come from files or other sources, ensure they follow the shape required by the endpoint (a list of objects containing filename and checksum). For example:
```
[
  {
    "filename": "fileA.fastq",
    "checksum": "d41d8cd98f00b204e9800998ecf8427e"
  },
  {
    "filename": "fileB.fastq",
    "checksum": "0cc175b9c0f1b6a831c399e269772661"
  }
]
```

