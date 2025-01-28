import requests
from hash_validator import convert_space_separated_to_json

def test_generate_checksums():
    """
    Test the /generate-checksums endpoint by providing a full GCS URI
    that includes the bucket name and optional path prefix.
    """
    payload = {
        "source_gcs_uri": "gs://centogene-raw-fqs/DRAGEN_WGS_V2",
        "destination_bucket": "transfer_checksum_api",
        "output_file_name": "centogene_raw_fqs_checksums.csv"
    }
    url = "http://127.0.0.1:8000/generate-checksums"
    response = requests.post(url, json=payload)
    print("Generate Checksums Response:", response.json())


def test_compare_checksums(json1, json2):
    payload = {
        "json1": json1,
        "json2": json2
    }
    url = "http://127.0.0.1:8000/compare-checksums"
    response = requests.post(url, json=payload)

    print("Status Code:", response.status_code)
    print("Compare Checksums Raw Response:", response.text)

    if response.ok:
        print("Compare Checksums Response (JSON):", response.json())
    else:
        print("Error occurred. Response is not valid JSON or returned an error status.")


def test_get_checksums():
    payload = {
        "checksum_bucket": "transfer_checksum_api",
        "checksum_file": "centogene_raw_fqs_checksums.csv"
    }
    url = "http://127.0.0.1:8000/get-checksums"
    response = requests.post(url, json=payload)
    # print("Get Checksums Response:", response.json())
    return response


if __name__ == "__main__":
    centogene_json = convert_space_separated_to_json("data/md5_cat_file.txt")
    gp2_request = test_get_checksums()
    gp2_json = gp2_request.json()
    # print(centogene_json)
    # print('#'*30)
    # print('#'*30)
    # print('#'*30)
    # print(gp2_json)
    # test_generate_checksums()
    test_compare_checksums(centogene_json, gp2_json)
    # test_get_checksums()





