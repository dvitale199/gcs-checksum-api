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
    source_gcs_uri: str
    destination_bucket: str
    output_file_name: str

class ChecksumItem(BaseModel):
    filename: str
    checksum: str

class CompareChecksumsRequest(BaseModel):
    first_checksums: List[ChecksumItem]
    second_checksums: List[ChecksumItem]

class GetChecksumsRequest(BaseModel):
    checksum_bucket: str
    checksum_file: str

def convert_space_separated_to_json(input_file):
    """
    Reads a space-separated file containing filename and checksum.
    Returns a JSON-formatted string of the data.
    
    :param input_file: Path to the space-separated file.
    :return: A JSON string representing the data.
    """
    data = []
    
    with open(input_file, 'r') as infile:
        for line in infile:
            line = line.strip()
            if line:
                filename, checksum = line.split()
                data.append({"filename": filename, "checksum": checksum})
    
    return json.dumps(data, indent=4)

def parse_gcs_uri(uri: str):
    """
    Parse a GCS URI of the form 'gs://bucket_name/optional/path'
    and return the (bucket_name, object_path_prefix).
    """
    if not uri.startswith("gs://"):
        raise ValueError("Invalid GCS URI. Must start with gs://")

    without_scheme = uri[len("gs://"):]
    parts = without_scheme.split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket_name, prefix

def decode_md5_hash(md5_hash_b64: str) -> str:
    """
    Decode an MD5 hash in base64-encoded format into its hex representation.
    """
    import base64
    import binascii
    decoded_bytes = base64.b64decode(md5_hash_b64)
    return binascii.hexlify(decoded_bytes).decode("utf-8")

@app.post("/generate-checksums")
def generate_checksums(request: GenerateChecksumsRequest):
    """
    Generate md5 checksums for all objects under the given GCS URI
    (e.g. gs://my-bucket/test_dir). Writes them to a CSV file in
    the specified destination bucket.

    The output file will contain two columns: filename and checksum.
    """
    storage_client = storage.Client()

    source_bucket_name, prefix = parse_gcs_uri(request.source_gcs_uri)
    source_bucket = storage_client.bucket(source_bucket_name)
    destination_bucket = storage_client.bucket(request.destination_bucket)

    blobs = source_bucket.list_blobs(prefix=prefix)
    output_buffer = io.StringIO()
    writer = csv.writer(output_buffer, delimiter=",")

    for blob in blobs:
        if not blob.md5_hash:
            raise HTTPException(
                status_code=500,
                detail=f"Blob {blob.name} has no md5 hash available."
            )
        md5_hex = decode_md5_hash(blob.md5_hash)

        # Remove the prefix from the filename so we don't include 'test_dir/'.
        relative_name = blob.name[len(prefix):].lstrip("/")
        writer.writerow([relative_name, md5_hex])

    output_blob = destination_bucket.blob(request.output_file_name)
    output_blob.upload_from_string(output_buffer.getvalue())

    return {"message": "Checksum file created successfully."}

@app.post("/compare-checksums")
def compare_checksums(request: CompareChecksumsRequest) -> Dict[str, List[str]]:
    """
    Compare two sets of filename/checksum pairs provided directly as JSON.
    Returns a dictionary with filenames that match, mismatch,
    and filenames found only in the first or second list.
    """
    first_checksums = {item.filename: item.checksum for item in request.first_checksums}
    second_checksums = {item.filename: item.checksum for item in request.second_checksums}

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