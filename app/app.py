from flask import Flask,request,jsonify
from flask_cors import CORS
import requests
import json
import time
import re 
from bs4 import BeautifulSoup
import os
import urllib 
 

app = Flask(__name__)
# r'/*' 是通配符，让本服务器所有的 URL 都允许跨域请求
CORS(app, resources=r"/*")

# 替换以下变量为实际的值
baseId = "appwcZdiU9CwICb9x"
tableIdOrName = "Lead_Enrichment"
recordId = "recYKMtbcWxLYpLKA"
api_token = "patSNai41M2pmpTLv.2182deccd9787acb57ca0e025f78bb2435920dc29bc9104cfa81b056ece51fbb"
 

proxies = {"https": "127.0.0.1:15236"}
url = f"https://api.airtable.com/v0/{baseId}/{tableIdOrName}/{recordId}"
tableUrl = f"https://api.airtable.com/v0/{baseId}/{tableIdOrName}"
headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}


# test usage: n8n returned json object
test_company_json = {
    "output": {
        "company_name": "American Drapery Systems, Inc.",
        "website_url": "https://www.americandrapery.com",
        "founded_year": "1977",
        "address": "Not Available (City and State available)",
        "city": "Golden Valley",
        "state_province": "Minnesota",
        "country": "USA",
        "business_description": "American Drapery Systems, Inc. is a family-owned and operated company with over 45 years of experience specializing in commercial window coverings. Their offerings include draperies, cubicle curtains, curtain track systems, and hardware. They also provide custom blinds, shades, and professional installation services. The company caters to a wide range of commercial customers such as hospitals, schools, medical facilities, corporate offices, and stadiums, focusing on delivering solutions that blend style, form, and function. They have evolved into a 'family of brands' including American Drapery Systems, American Track Supply, Blackout Curtains, and CustomCube.",
        "primary_services": [
            "Commercial window coverings manufacturing",
            "Draperies",
            "Cubicle curtains",
            "Curtain track systems and hardware",
            "Motorization of window coverings",
            "Professional installation services",
            "Consultation for window covering solutions",
            "Custom blinds",
            "Custom shades",
        ],
        "business_type": "Manufacturer, Service Provider",
        "industry_sector": "Building Materials & Equipment, Commercial Window Coverings, Construction",
        "key_markets": [
            "Commercial sector clients (hospitals, schools, medical facilities, corporate offices, stadiums)",
            "Upper Midwest (historical primary service area, current broader reach implied)",
        ],
        "key_suppliers": [],
        "employee_count": "Fewer than 50 employees",
        "annual_revenue": "$3.7 million USD",
        "ceo": "Not Specified (Berek and Josh are owners/managers)",
        "founders": [],
        "key_executives": [
            "Berek (Owner/Manager)",
            "Josh (Owner/Manager)",
            "Duane Cook (Lead Estimator/Sales)",
            "Steve Weiland (Warehouse/Production Manager)",
        ],
        "certifications": [],
        "awards": [],
        "notable_clients": [
            "Hospitals",
            "Schools",
            "Medical facilities",
            "Corporate offices",
            "Stadiums",
        ],
        "subsidiaries": ["American Track Supply", "Blackout Curtains", "CustomCube"],
        "research_date": "2024-07-28",
        "sources_consulted": [
            "https://americandrapery.com/a-family-of-brands-the-evolution-of-american-drapery-systems/",
            "https://craft.co/american-drapery-systems",
            "https://www.zoominfo.com/c/american-draperies--blinds-inc/6197001",
            "https://www.zippia.com/american-drapery-blind-careers-948846/history/",
            "https://americandrapery.com/about-american-drapery-systems-inc/",
        ],
        "confidence_score": "High",
        "data_freshness": "Founded Year, Location, Business Description, Primary Services, Business Type, Key Personnel, Subsidiaries: Current; Annual Revenue: 2018; Employee Count: Estimated/Recent (no specific year provided, but reflects current operations)",
        "notes": "The exact street address for the headquarters was not explicitly found across the consulted sources. Revenue and employee count are estimates from business intelligence platforms and may not reflect the absolute most current figures. No specific CEO title was found; Berek and Josh are identified as owners/managers. The company highlights key managers rather than a single CEO.",
    }
}

'''
****************************** 
helper functions start ****************************** 
'''

# Method 1: Fix the specific escape issue
def fix_json_escape_errors(json_str):
    """Fix common JSON escape issues"""

    # Fix invalid escape sequences
    # Replace \' with just ' (single quote doesn't need escaping in JSON)
    fixed = json_str.replace("\\'", "'")

    # Fix any other common issues
    # Remove extra whitespace that might cause issues
    fixed = re.sub(r"\s+", " ", fixed)

    return fixed


# Method 2: Clean and fix JSON string comprehensively
def clean_json_string(json_str):
    """Comprehensive JSON string cleaning"""

    # Remove extra whitespace and newlines within the JSON structure
    # but preserve intentional newlines in string values
    lines = json_str.split("\n")
    cleaned_lines = []

    for line in lines:
        # Remove leading/trailing whitespace but preserve content
        cleaned_line = line.strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    # Join back
    cleaned = "\n".join(cleaned_lines)

    # Fix escape sequences
    cleaned = cleaned.replace("\\'", "'")

    return cleaned

# convert to json from n8n returned company data
def extract_json_from_llm_response(response_text):
    """
    Extract and parse JSON from language model response that contains JSON within a dictionary string.

    Args:
        response_text (str): The response text containing JSON

    Returns:
        dict: Parsed JSON object
    """

    # Method 1: Extract JSON from the 'output' key if it's a string representation of a dict
    try:
        # Use eval to parse the outer dictionary structure (be careful with eval in production)
        # This handles the case where the response is a string representation of a dict
        outer_dict = eval(response_text)

        # Extract the JSON string from the 'output' key
        json_string = outer_dict["output"]

        # Remove the markdown code block markers if present
        json_string = re.sub(r"^```json\n", "", json_string)
        json_string = re.sub(r"\n```$", "", json_string)

        # Parse the JSON string
        parsed_json = json.loads(json_string)

        return parsed_json

    except Exception as e:
        print(f"Method 1 failed: {e}")

        # Method 2: Use regex to extract JSON content
        try:
            # Find JSON content between ```json and ```
            json_match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            if json_match:
                json_string = json_match.group(1)
                print("2.", json_string, type(json_string))
                parsed_json = json.loads(json_string)
                print("2.1", parsed_json)
                return parsed_json
            else:
                # Method 3: Try to find JSON-like content directly
                # Look for content that starts with { and ends with }
                try:
                    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                    if json_match:
                        json_string = json_match.group(0)
                        print("3.0", json_string)
                        parsed_json = json.loads(json_string)
                        return parsed_json
                except Exception as e3:
                    print(f"Method 3 failed: {e3}")
                    print("=== First time Fix escape errors ===")
                    try:
                        fixed_json = fix_json_escape_errors(json_string)
                        data = json.loads(fixed_json)
                        print("✓ Successfully parsed JSON!")
                        print(f"Company: {data['company_name']}")
                        print(f"Founded: {data['founded_year']}")
                        print(f"Employees: {data['employee_count']}")
                        return data
                    except Exception as e:
                        print(f"✗ First Fix failed: {e}")
                        print("Second time Fix: Comprehensive cleaning ===")
                        try:
                            cleaned_json = clean_json_string(json_string)
                            data = json.loads(cleaned_json)
                            print("✓ Successfully parsed with cleaning!")
                            print(f"Business type: {data['business_type']}")
                            print(f"Industry: {data['industry_sector']}")
                            return data
                        except Exception as e:
                            print(f"✗ Fix failed: {e}")
                            return None
        except Exception as e2:
            print(f"Method 2 failed: {e2}")
            print("=== First time Fix escape errors ===")
            try:
                fixed_json = fix_json_escape_errors(json_string)
                data = json.loads(fixed_json)
                print("✓ Successfully parsed JSON!")
                print(f"Company: {data['company_name']}")
                print(f"Founded: {data['founded_year']}")
                print(f"Employees: {data['employee_count']}")
                return data
            except Exception as e:
                print(f"✗ First Fix failed: {e}")
                print("Second time Fix: Comprehensive cleaning ===")
                try:
                    cleaned_json = clean_json_string(json_string)
                    data = json.loads(cleaned_json)
                    print("✓ Successfully parsed with cleaning!")
                    print(f"Business type: {data['business_type']}")
                    print(f"Industry: {data['industry_sector']}")
                    return data
                except Exception as e:
                    print(f"✗ Fix failed: {e}")
                    return None


'''
extract contact name and his linkedIN url from google SERP 
''' 
def extract_linkedin_contacts(html_content):
    """
    Extract the second！！ contact name and LinkedIn URL from Google SERP HTML file.
    
    Args:
        html_file_path (str): Path to the HTML file
        
    Returns:
        dict: Dictionary containing 'name' and 'linkedin_url', or None if not found
    """
    
    try:
        # Read the HTML file
        # with open(html_file_path, 'r', encoding='utf-8') as file:
        #     html_content = file.read()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        contacts = []
        
        # Find all divs with class "LC20lb MBeuO DKV0Md" (contact names)
        name_divs = soup.find_all('h3', class_='LC20lb MBeuO DKV0Md')
        # print("arrays: ",name_divs)

        for name_div in name_divs:
            # Extract full text content
            full_text = name_div.get_text(strip=True)
            # print("contact: ",full_text)
            # Extract name before the first "-"
            if '-' in full_text:
                name = full_text.split('-')[0].strip()
            else:
                name = full_text.strip()

            if ',' in name:
                name = name.split(',')[0].strip()
            else:
                name = name.strip()    
            # print(f"Debug - name after split: {name}")
            # print(f"Debug - name type: {type(name)}")
            
            # Ensure name is a string, not a tuple
            if isinstance(name, tuple):
                name = name[0] if name else ""
            
            # Find the corresponding LinkedIn URL
            # Look for the parent anchor tag with class "zReHs"
            parent_a = name_div.find_parent('a', class_='zReHs')
            
            linkedin_url = None
            # print("outer link: ",parent_a)
            if parent_a and parent_a.get('href'):
                href = parent_a.get('href')
                # Check if it's a LinkedIn URL
                if 'linkedin.com' in href:
                    linkedin_url = href
            
            # If we found both name and LinkedIn URL, return the first one
            if name and linkedin_url:
                 contacts.append({
                    'name': str(name),
                    'linkedin_url': linkedin_url
                })
        # return the second contact,the first is the company by some reason?
        # print("contacts: ", contacts)
        return contacts[1]
        
    except FileNotFoundError:
        # print(f"Error: File '{html_file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

# google search linkedIn contact with give company name
def get_SERP_from_google_linkedin_search(company):
    
    headers = { 
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "x-client-data": "CK21yQEIjLbJAQimtskBCKmdygEIs+TKAQiTocsBCIurzAEI95jNAQiFoM0BGKfqzQE="
}
    cookies = {
        "SEARCH_SAMESITE": "CgQIoJ4B",
        "SID": "g.a000ywjB0pNtdUcan9FB0DHw8lOQq73SWno9nAVU1Rt_itHDY3G2a-a3kzpt22kdo6OyFEY_1wACgYKAfcSARASFQHGX2MishA53dUtRhfWVm960BXWIhoVAUF8yKoJh_cfFXPjY2-rQDSKy2Vr0076",
        "__Secure-1PSID": "g.a000ywjB0pNtdUcan9FB0DHw8lOQq73SWno9nAVU1Rt_itHDY3G2PvlRHNYmfg3oVDioeN-togACgYKAToSARASFQHGX2MiVvkdVesnJmEN6mKKYx-gDxoVAUF8yKrB3iXU8GqdBLBKzFh0NXPU0076",
        "__Secure-3PSID": "g.a000ywjB0pNtdUcan9FB0DHw8lOQq73SWno9nAVU1Rt_itHDY3G2AyiyDP2BOzIF_OYfax-9rAACgYKAXQSARASFQHGX2MiVxG0mN1UVj4mwIyfLo0jBRoVAUF8yKrmMjxwOEPX2rNaa_qkRNzO0076",
        "HSID": "AzV0a8LGq4mhhlcLR",
        "SSID": "A_nVtA_XRI1fvqyXj",
        "APISID": "HwOU1Ro9P20XBL1N/Ad7nfa0sm__IJVCNu",
        "SAPISID": "9HnOnS8Qcxpxk6f8/AKx-SCJCw8gR77rT1",
        "__Secure-1PAPISID": "9HnOnS8Qcxpxk6f8/AKx-SCJCw8gR77rT1",
        "__Secure-3PAPISID": "9HnOnS8Qcxpxk6f8/AKx-SCJCw8gR77rT1",
        "AEC": "AVh_V2gFnTc5AyKStZRhToorzXOl1htSSNDn22UbTphEb70Mz7nZXLAS_Ls",
        "NID": "525=Le2FOzz2JN7bQ9bvCWmGPxTf-avGWIxL8T--_LW6Rd6lsXFIR17MYDx5GMyPDrEpssmXLdJ1v6CVE81_2a8u2v5ALGnie-MGOLXd0AhDKXsvnSeo5N5WkzE07fhVFQbSaqjwpnPtYhqHXFq_Jr-afbRQzitRwa_VFeU6P6e2jYDF0WEfvezVI32yWdqH7_tZmWBPVLpBMbO5R24JKHT_QCj6I7vU_jbc1yxflvIJSuM8chZb2J5k4cd7f3HgQVAx-Y-p-dX4fH_Wca_4EofTsoC80aHPvI7HDLSgvAOooiBcZ_xYZ2u_Gn6OtwflO6OJthmbXljG7ylCJVhYD30cmk4jF2zfuYhdP1bEmU5D9Y3mgM4nRCHpAC6eCKDZaGtb3hsRnSn1llubivB0s_EXDHp_4zdI7uskIUda0snlMrT3kejvlgFl_0RLh75NM3K1GOzWPdpL_m7Q4xmo2NO28iyJzw-VnQVD7I19MKdNCBR1ZNrlCACPUtL_eOY27GeysmRUp8WvfjhIHnnLvcgAnDIZiTBrc__FmSa02RquO5pzUytln0RmkebFgoBkYojohekS-2jNOJmblkZu8yR38ovcP_aJFnkokHLLUcu0knvH1BmuwCvVyYxblxhThne0SP1_9r6WgIGdy4B6LX3fzMB7NIZqjiwVMSNfsfwANEW7Toqbl2PA-hkh3sN-AVRcmbeDu9V6kZG1OMjl5gVtOp5J7Czr-t-joS3_EGjQTA4qo4YycbZF8sKIzgD7K8MBs5EFQbvEhVPMpogG__-5le6dAdd5rzv8rWW69CbuadcjI-vzpm03GOo_u6wbIpxtEFd5WnF_xp7pzo194hMGpo3XVRx7nV5MhqAX1lT5JeLcSnWQDw0yzICnrx8d8QzKZUrRzb3qGfQae9tsoOaU9byIdGnRVTSwY191adS_emOxvT8GAvmkxpyfv3lm-PeHZM20_Du61s3b0LepwHNC3ZdwCJKfLU7XVo1reDEhQcq0P7QrZ_d7zWfwQgPDYK9DwUFAA1U7l2ClpfXDuubXiY8Is7tOhd9a_34xjbpGzBd-ricQcgTJI5w2_qbJGuoKDCbarvNEoL4NUS4",
        "__Secure-1PSIDTS": "sidts-CjEB5H03P9FQveoKPazkpHR9_awMl-jbD61EC0bifY40PTuU2_gaVxNhLEKY3LK0p4ijEAA",
        "__Secure-3PSIDTS": "sidts-CjEB5H03P9FQveoKPazkpHR9_awMl-jbD61EC0bifY40PTuU2_gaVxNhLEKY3LK0p4ijEAA",
        "SIDCC": "AKEyXzWaoDqJdRpnxSKgprXElN9gDmA0VRk3QEy38cO3s8z9VFXbG09UIM6TDvzbT32_2QgI0bw",
        "__Secure-1PSIDCC": "AKEyXzUJ73ADHgH0wrsnbOmDBIr_RXcYg8xeYj02Y0bjIV9KBQ8m1smkpV64U5qbn_fR4GQy7Q",
        "__Secure-3PSIDCC": "AKEyXzX8-hWM5FL6zN-bzcdjd3gDMDjVsX8kwdkgSWY4wHIKrE4FmLvSAOo2l6CpfbmxjtchQhM"
    } 
    # query = "site^%^3Alinkedin.com^%^2Fin American Drapery Systems" 
    readable_query = f"site:linkedin.com/in {company}"
    # Then URL encode it 用这个搜索出结果就不对了
    # encoded_query = urllib.parse.quote(readable_query, safe='')
    # print("query: ",readable_query)
    url = "https://www.google.com/search"
    params = {
        "q": readable_query,
        "newwindow": "1",
        "sca_esv": "81bfa16c567e5cd8",
        "sxsrf": "AE3TifMtxVwtFrqtzIf0fpUPPKi6qED_Jw^%^3A1752418610042",
        "source": "hp",
        "ei": "MslzaKGJAaD2kPIPiY3SsA8",
        "iflsig": "AOw8s4IAAAAAaHPXQrvYZJl983yGstuuJUwdMc4i-knS",
        "ved": "0ahUKEwih6v2FjLqOAxUgO0QIHYmGFPYQ4dUDCBk",
        "uact": "5",
        "oq": "site^%^3Alinkedin.com^%^2Fin American Drapery Systems",
        "gs_lp": "Egdnd3Mtd2l6Ii1zaXRlOmxpbmtlZGluLmNvbS9pbiBBbWVyaWNhbiBEcmFwZXJ5IFN5c3RlbXNIi94CULIMWNzJAnABeACQAQCYAYcDoAGmKqoBBjItMjEuMbgBA8gBAPgBAfgBApgCBqACjQuoAgrCAgcQIxgnGOoCwgILEAAYgAQYkQIYigXCAg4QLhiABBixAxiDARjUAsICCBAuGIAEGOUEwgIFEAAYgATCAggQLhiABBixA8ICERAuGIAEGLEDGNEDGIMBGMcBwgILEAAYgAQYsQMYgwHCAgsQLhiABBjRAxjHAcICChAAGIAEGEMYigXCAgsQLhiABBjHARivAcICDhAAGIAEGLEDGIMBGIoFwgIQEC4YgAQY0QMYQxjHARiKBcICDRAAGIAEGLEDGEMYigXCAggQABiABBixA8ICDhAuGIAEGLEDGNEDGMcBwgILEC4YgAQYsQMYgwHCAgcQABiABBgKmAML8QWFCQ-8zqZFQJIHBzEuMC40LjGgB_8-sgcFMi00LjG4B4ELwgcFMi01LjHIBx8",
        "sclient": "gws-wiz"
    }
    response = requests.get(url, headers=headers, cookies=cookies, params=params)

    # print("goolge result: ", response.text)
    # print(response)  
    # 这里的第一个总是公司，与页面不一样！所以取第二个联系人
    contact = extract_linkedin_contacts(response.text)
    
    if not contact:
        # print("First LinkedIn contact found:")
        # print("-" * 30)
        # print(f"Name: {contact['name']}")
        # print(f"LinkedIn: {contact['linkedin_url']}") 
        # else:
        print("No LinkedIn contact found in the HTML file.")  
    return contact 

'''
****************************** 
helper functions ends ****************************** 
'''
@app.route("/")
def home():
    return "hello，product app project!"

# clear table while keeping record IDs
@app.route("/clearTable", methods=["GET"])
def clear_airtable():
    # 首先获取所有记录
    response = requests.get(tableUrl, headers=headers)
    # print("response: ", response.json())
    records = response.json().get("records", [])
    # print("records: ",records)

    # 为每条记录创建更新请求，清空所有字段
    for record in records:
        record_id = record["id"]
        # fields = {key: None for key in record['fields'].keys()}
        fields = {key: None for key in record["fields"].keys() if key != "RECORD_ID"}

        update_data = {"fields": fields}
        # print(update_data)
        update_url = f"{tableUrl}/{record_id}"
        requests.patch(update_url, headers=headers, json=update_data)
        time.sleep(0.2)  # 放慢速度，embeded table 才能够实时响应

    print("已经清空表格了！")
    return "POST"

@app.route("/getCompany", methods=["GET"])
def update_airtable_Company():
    '''
    IGNORE this function!!! work will be done from frontend now!!! 

    ''' 
    # update 2 fields
    data = {
        "fields": {
            "公司名称": "Adwards101 Drapery Systems",
            "公司网站": "https://www.adwardsrapery.com",
        }
    }
    # response = requests.patch(
    #     url, headers=headers, data=json.dumps(data), proxies=proxies
    # )

    # # Update a record
    # print("Updating company columns...")
    # # if updated_record:
    # if response.status_code == 200:
    #     print("Company updated successfully!")
    #     # print(f"Updated fields: {updated_record['fields']}")
    # else:
    #     print("Failed to update company")
    return "POST"

# http://127.0.0.1:5000/researchCompany?url=https://www.americandrapery.com
@app.route("/researchCompany", methods=["GET"])
def update_airtable_Profile():
    ''''
     param: company url
     api search company info, extract json
     update company columns to the airtable
    '''
    print("enter")
    print("request ", request.args)
    companyUrl = request.args.get('url', "", type=str)
    print(companyUrl)
    # 1. n8n api return company information
    n8n_url = f"https://ctgcloud.app.n8n.cloud/webhook-test/company-research?url={companyUrl}"

    print(n8n_url)
    response = requests.request("GET", n8n_url)
    # print(response.text)
    # , proxies=proxies

    # Convert the response to JSON
    json_data = extract_json_from_llm_response(response.text)

    if json_data:
        # print(json.dumps(json_data, indent=2))  
        # 有时会返回{'error'：'KeyError: 'output''} valid json，but not content！
        if 'error' in json_data:
            return None
        # You can now access the data as a regular Python dictionary
        # print(f"\nCompany Name: {json_data['company_name']}")
    else:
        print("Failed to extract JSON from the response")
        return None

    # 2. Update company related records
    print("Updating company columns...")
    output = json_data["output"]
    company_name = output["company_name"]
    website_url = output["website_url"]
    country = output["country"]
    print(country, type(country))
    business_description = output["business_description"]
    # print(business_description)
    employee_count = output["employee_count"] if output["employee_count"].strip() != "Not Available" else "30-50"  
    # print(employee_count)
    business_type = output["business_type"]
    # print(business_type)
    # 行业
    industry_sector = output["industry_sector"]
    # print(industry_sector)
    annual_revenue = output["annual_revenue"] if output["annual_revenue"].strip() != "Not Available" else "$32,745,768"  
    # print(annual_revenue)

    updated_fields = {
        "公司名称": company_name,
        "公司网站": website_url,
        "国家": country,
        "员工数量": employee_count,
        "行业": industry_sector,
        "年营业额": annual_revenue,
        "公司介绍": business_description,
        "业态": business_type,
        "ICP匹配度指数": 0.75,  # 如果78%，则返回status=422，但不报错！
    }
    # print(updated_fields)
    data = {"fields": updated_fields}
    try:
        response = requests.patch(
            url, headers=headers, data=json.dumps(data) )
        if response.status_code == 200:
            print("Profile updated successfully!")
        else:
            print("Failed to update profile ", response.status_code)
    except Exception as e:
        print(f"发生错误: {e}")

    return "POST"

# http://127.0.0.1:5000/getManager?company=%22American%20Drapery%20Systems%22
@app.route("/getManager", methods=["GET"])
def update_airtable_Manager():
    '''
    param: company name
    google search likedIn contact of this company
    using api get this contact's email box using his linkedIn url
    update contact, linkedIn url, email box to airtable
    '''
    company = request.args.get('company', "", type=str)
    # print(company)
    # goolge search this company's linkedIn contact(pick the 2nd one in SERP)
    contact = get_SERP_from_google_linkedin_search(company)
    manager = contact["name"] 
    linkedin_url = contact["linkedin_url"]
    # print(linkedin_url)
    #get his email box via API call
    response = requests.post(
        "https://app.findymail.com/api/search/linkedin",
        headers={
        "Content-Type": "application/json",
        "Authorization": "aa7S3SIaX6OGpjMpygdMhBeAtO7IajCtaPU11cqY1fdb898c"
        },
        json={
        "linkedin_url": linkedin_url,
        "webhook_url": None
        } 
    )
    email = response.text
    # {"message":"Unauthenticated."}
    print(email) 
    # update contact, linkedIn url, email box to airtable  
    print("Updating manager columns...")

    updated_fields = {
        "采购主管姓名": manager,
        "采购主管邮箱": email, 
        "LinkedIn URL": linkedin_url, 
    } 
    data = {
        "fields": updated_fields
    }

    # response = requests.patch(url, headers=headers, data=json.dumps(data),proxies=proxies)
 
    # if response.status_code == 200:
    #     print("Manager updated successfully!")   
    # else:

    #     print("Failed to update manager")

    return ("POST")

@app.route("/writeEmail", methods=["GET", "POST"])
def update_airtable_email():
    '''
    request body: contact, company site url
    update email body to airtable
    '''
    #1. get contact from request (页面还传入一个公司网址url进来，但是code中没有用，而用record ID找到公司介绍。)
    # Support both form data and JSON
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict() 
    contact = data.get('contact') 

    # if not contact:
    #     return jsonify({
    #         "status": "error",
    #         "message": "contact name is required for writing email"
    #     }), 400
    
    #2.get company description from airtable with the record id
    response = requests.get(url, headers=headers )
    # print("response: ", response.json())
    companyDesc = response.json().get('fields',{})['公司介绍'] 
    # print(companyDesc) 

    #3.n8n API write personalized Email  
    # Edata = {
    #     "name": contact,
    #     "company":companyDesc  
    # }

    # n8n_url = "https://ctgcloud.app.n8n.cloud/webhook-test/write-email"

    # response = requests.request("POST", n8n_url, json=Edata, proxies=proxies)
 
    # print(f"Status Code: {response.status_code}")
    # print(f"Response: {json.dumps(response.json(), indent=2)}")
    # # Convert the response to JSON
    # json_data =  response.json()

    # if json_data: 
    #     if 'error' in json_data:
    #         return None 
    # else:
    #     print("Failed to extract JSON from the response")
    #     return None

    #4. update table with email body
    # print("Updating email column...")
    # email = json_data["output"]
    # # Update a record 
    # print(email)
    
    # updated_fields = {
    #     "个性化邮件": email }

    # data = {
    #     "fields": updated_fields
    # }

    # response = requests.patch(url, headers=headers, data=json.dumps(data),proxies=proxies)

    # if response.status_code == 200:
    #     print("Profile updated successfully!")  
    # else:
    #     print("Failed to update email")
    return ("POST") 

if __name__ == "__main__":
    app.run(host="0.0.0.0")  # 启用调试模式
