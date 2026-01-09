import requests

url = "https://prm-api.qa.uniuni.com/orders/printlabel"

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vcHJtLWFwaS51bml1bmkuY29tL3N0b3JlYXV0aC9jdXN0b21lcnRva2VuIiwiaWF0IjoxNzY3OTY3NTAzLCJuYmYiOjE3Njc5Njc1MDMsImV4cCI6MTc2ODA1MzkwMywiY291bnRyeSI6IlVTIiwicGFydG5lcl9pZCI6Mzc5LCJuYW1lIjoiSGFydmljIGludGVybmF0aW9uYWwiLCJhcGlfdmVyc2lvbiI6IjIifQ.UgCM4-u-OQsuGTVkSWxY0YzYn0-yp8NCtNicXtGwGW0"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/pdf"
}

body = {
    "packageId": "UUS6153790882160798",
    "labelType": 6,
    "labelFormat": "pdf",
    "type": "pdf"
}

response = requests.post(url, headers=headers, json=body, stream=True)

if response.status_code == 200:
    with open("report.pdf", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("PDF downloaded successfully")
else:
    print(response.status_code, response.text)