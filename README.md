# Nichenet Proxy Client

## Description 
This API works by front-end users querying our proxy client, which is the server we use to create and authenticate API keys. From there, the proxy client forwards the queries to validators that query the miners, and then the result is returned back the same way.

Reference this [document](https://docs.nichetensor.com/) regarding how this works.

## Overview of current API
![alt text](overview.png)

## Setup

1. Create virtual environment
```bash
python3 -m venv myvenv
```

2. Activate the virtual environment
```bash
source myvenv/bin/activate
```

3. Install packages
```bash
pip install -r requirements.txt
```

4. Run the application
```bash
uvicorn app:app.app --reload
```

## Credential Retrieval Validation Steps

The `get_credentials` process is designed to verify the identity and authenticity of a validator's request. This involves checking the request's timestamp and verifying its digital signature.

1. **Timestamp Expiry Check**
   - Ensure the `nonce` (timestamp) in the request is within an acceptable timeframe (`REQUEST_EXPIRY_LIMIT_SECONDS`).
   - If the request exceeds this time limit, it’s considered expired and is rejected with an error.

2. **Signature Verification**
   - Construct a message using `validator_info.postfix`, the validator’s unique address, and the `nonce`.
   - Use the validator's public key to verify that the `signature` provided matches this constructed message.
   - If the signature is invalid, the request is marked unverified and is rejected.

3. **Error Handling**
   - If any issues arise—such as an expired request, invalid signature, or missing information—the process returns an error indicating the specific failure reason.

This streamlined validation logic ensures that only timely, authentic requests from verified validators are accepted.
