from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import base64
import csv
import io
import json
from google.cloud import storage

app = FastAPI()

class GenerateChecksumsRequest(BaseModel):
    source_bucket: str
    destination_bucket: str
    output_file_name: str

class CompareChecksumsRequest(BaseModel):
    first_checksum_bucket: str
    first_checksum_file: str
    second_checksum_bucket: str
    second_checksum_file: str

class GetChecksumsRequest(BaseModel):
    checksum_bucket: str
    checksum_file: str

def decode_md5_hash(encoded_md5: str) -> str:
    """
    decode a base64-encoded md5 hash to a hexadecimal string.
    """
    decoded = base64.b64decode(encoded_md5).hex()
    return decoded

@app.post("/generate-checksums")
def generate_checksums(request: GenerateChecksumsRequest):
    """
    generate md5 checksums for all objects in the specified source bucket
    and write them to a file in the specified destination bucket. The file
    will contain two columns: filename and checksum.
    """
    storage_client = storage.Client()

    source_bucket = storage_client.bucket(request.source_bucket)
    destination_bucket = storage_client.bucket(request.destination_bucket)

    blobs = source_bucket.list_blobs()
    output_buffer = io.StringIO()
    writer = csv.writer(output_buffer, delimiter=",")
    
    for blob in blobs:
        if not blob.md5_hash:
            raise HTTPException(
                status_code=500,
                detail=f"blob {blob.name} has no md5 hash available."
            )
        md5_hex = decode_md5_hash(blob.md5_hash)
        writer.writerow([blob.name, md5_hex])

    output_blob = destination_bucket.blob(request.output_file_name)
    output_blob.upload_from_string(output_buffer.getvalue())

    return {"message": "checksum file created successfully."}

@app.post("/compare-checksums")
def compare_checksums(request: CompareChecksumsRequest) -> Dict[str, List[str]]:
    """
    with lists of files that have matching checksums, mismatched checksums,
    compare two checksum files (by filename) in gcs. return a dictionary
    and files found in only one of the lists.
    """
    storage_client = storage.Client()

    first_bucket = storage_client.bucket(request.first_checksum_bucket)
    second_bucket = storage_client.bucket(request.second_checksum_bucket)

    first_blob = first_bucket.blob(request.first_checksum_file)
    second_blob = second_bucket.blob(request.second_checksum_file)

    first_data = first_blob.download_as_text()
    second_data = second_blob.download_as_text()

    first_checksums = {}
    second_checksums = {}

    first_reader = csv.reader(io.StringIO(first_data), delimiter=",")
    for row in first_reader:
        filename, checksum = row
        first_checksums[filename] = checksum

    second_reader = csv.reader(io.StringIO(second_data), delimiter=",")
    for row in second_reader:
        filename, checksum = row
        second_checksums[filename] = checksum

    matching = []
    mismatching = []
    only_in_first = []
    only_in_second = []

    all_files = set(first_checksums.keys()).union(set(second_checksums.keys()))
    for filename in all_files:
        if filename in first_checksums and filename in second_checksums:
            if first_checksums[filename] == second_checksums[filename]:
                matching.append(filename)
            else:
                mismatching.append(filename)
        elif filename in first_checksums and filename not in second_checksums:
            only_in_first.append(filename)
        elif filename not in first_checksums and filename in second_checksums:
            only_in_second.append(filename)

    return {
        "matching": matching,
        "mismatching": mismatching,
        "only_in_first": only_in_first,
        "only_in_second": only_in_second
    }

@app.post("/get-checksums")
def get_checksums(request: GetChecksumsRequest):
    """
    retrieve the checksum file from gcs and return the contents in json format.
    each item in the json list contains the keys 'filename' and 'checksum'.
    """
    storage_client = storage.Client()
    checksum_bucket = storage_client.bucket(request.checksum_bucket)
    checksum_blob = checksum_bucket.blob(request.checksum_file)

    if not checksum_blob.exists():
        raise HTTPException(
            status_code=404,
            detail="checksum file not found in specified bucket."
        )

    file_data = checksum_blob.download_as_text()
    reader = csv.reader(io.StringIO(file_data), delimiter=",")
    checksums_list = []

    for row in reader:
        filename, checksum = row
        checksums_list.append({"filename": filename, "checksum": checksum})

    return {"checksums": checksums_list}