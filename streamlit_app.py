import streamlit as st
import csv
import requests
from PIL import Image
from io import BytesIO
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
from datetime import datetime
import os

# Dropbox app credentials
APP_KEY = "omdsa3mo6ksvm2d"
APP_SECRET = "bh3w7v65lplye4h"

# Custom CSS

st.markdown("""
<style>
    .main {
        padding: 2rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stTextInput>div>div>input {
        background-color: #ffffff;
    }
    .stNumberInput>div>div>input {
        background-color: #ffffff;
    }
    .stFileUploader>div>div>button {
        background-color: #008CBA;
        color: white;
    }
    h1 {
        color: #2C3E50;
    }
    h2 {
        color: #34495E;
    }
    .stSuccess {
        background-color: #D4EDDA;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .stWarning {
        background-color: #FFF3CD;
        color: #856404;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
               /* Hide Streamlit header */
    header {visibility: hidden;}
    /* Hide Streamlit footer */
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Function to get Dropbox access token
def get_dropbox_auth():
    auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)
    authorize_url = auth_flow.start()
    
    st.write("1. Click on the link to authorize this app:")
    st.markdown(f"[Authorize Dropbox]({authorize_url})")
    st.write("2. Click 'Allow' (you might have to log in first).")
    st.write("3. Copy the authorization code.")
    
    auth_code = st.text_input("Enter the authorization code here:")
    
    if auth_code:
        try:
            oauth_result = auth_flow.finish(auth_code)
            access_token = oauth_result.access_token
            st.success("Successfully authenticated with Dropbox!")
            return access_token
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None
    return None

# Function to download and resize image
def download_and_resize_image(url, width, height, username):
    try:
        response = requests.get(url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        image = image.convert("RGBA")
        aspect_ratio = image.width / image.height
        if aspect_ratio > width / height:
            new_width = width
            new_height = int(width / aspect_ratio)
        else:
            new_width = int(height * aspect_ratio)
            new_height = height
        resized_image = image.resize((new_width, new_height))
        canvas = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        x = (width - new_width) // 2
        y = (height - new_height) // 2
        canvas.paste(resized_image, (x, y))
        rgb_image = canvas.convert("RGB")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        resized_image_path = f"resized_image_{timestamp}_{username}.jpg"
        rgb_image.save(resized_image_path)
        return resized_image_path
    except (requests.exceptions.RequestException, IOError) as e:
        st.error(f"Error occurred while downloading/resizing image: {e}")
        return None

def upload_to_dropbox(image_path, access_token):
    dbx = dropbox.Dropbox(access_token)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_file_name = f"resized_image_{timestamp}.jpg"
    with open(image_path, "rb") as f:
        response = dbx.files_upload(f.read(), "/{}".format(unique_file_name))
    image_link = dbx.sharing_create_shared_link_with_settings(response.path_display).url
    return image_link

def process_csv_file(file, column_names, replace_column_names, width, height, access_token, username):
    reader = csv.reader(file)
    header = next(reader)
    total_rows = sum(1 for row in reader)
    file.seek(0)
    next(reader)  # Skip header again
    
    with open("output.csv", "w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(header)
        for i, row in enumerate(reader):
            for column_name, replace_column_name in zip(column_names, replace_column_names):
                column_index = int(column_name) - 1
                replace_column_index = int(replace_column_name) - 1
                if 0 <= column_index < len(row) and 0 <= replace_column_index < len(row):
                    main_img_url = row[column_index]
                    if main_img_url:
                        resized_image_path = download_and_resize_image(main_img_url, width, height, username)
                        if resized_image_path:
                            new_link = upload_to_dropbox(resized_image_path, access_token)
                            row[replace_column_index] = new_link
                            st.success(f"Image resized and link replaced: {new_link}")
                            os.remove(resized_image_path)
            writer.writerow(row)
            progress_bar.progress((i + 1) / total_rows)
            status_text.text(f"Processing row {i+1} of {total_rows}")

# Main Streamlit app code
st.title("🖼️ Image Resizing App with Dropbox OAuth")
st.write("Authenticate with Dropbox, upload a CSV file with image links, and specify the columns to process.")

# Add Dropbox authentication
access_token = st.session_state.get('access_token')
if not access_token:
    st.header("🔐 Dropbox Authentication")
    access_token = get_dropbox_auth()
    if access_token:
        st.session_state['access_token'] = access_token

if access_token:
    st.header("📁 File Upload")
    uploaded_file = st.file_uploader("Upload a CSV file", type=['csv'])
    
    if uploaded_file is not None:
        st.header("⚙️ Processing Options")
        col1, col2 = st.columns(2)
        with col1:
            column_names = st.text_input("Image URL columns (comma-separated)")
            width = st.number_input("Resize width", min_value=1, value=300)
        with col2:
            replace_column_names = st.text_input("Replace columns (comma-separated)")
            height = st.number_input("Resize height", min_value=1, value=300)
        
        username = st.text_input("Enter your username")

        if st.button("🚀 Start Processing"):
            st.header("🔄 Processing")
            progress_bar = st.progress(0)
            status_text = st.empty()

            with open("temp.csv", "wb") as temp_file:
                temp_file.write(uploaded_file.getvalue())

            with open("temp.csv", "r") as local_file:
                column_names = column_names.replace(" ", "").split(",")
                replace_column_names = replace_column_names.replace(" ", "").split(",")
                process_csv_file(local_file, column_names, replace_column_names, width, height, access_token, username)

            os.remove("temp.csv")

            st.success("✅ Processing complete. Click the button below to download the output file.")

            with open("output.csv", "rb") as output_file:
                csv_data = output_file.read()

            st.download_button("📥 Download Output File", csv_data, file_name="output.csv", mime="text/csv")
else:
    st.warning("⚠️ Please authenticate with Dropbox to use this app.")

# Footer
st.markdown("---")
st.markdown("Made with ❤️ by Avid Brio")
