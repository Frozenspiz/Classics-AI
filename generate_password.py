import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os

st.title("ClassicsAI Password Generator")

with st.form("password_form"):
    username = st.text_input("Username")
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    submitted = st.form_submit_button("Generate Password Hash")
    
    if submitted:
        if password != confirm_password:
            st.error("Passwords do not match!")
        else:
            # Generate password hash
            hashed_password = stauth.Hasher([password]).generate()[0]
            
            st.success(f"Password hash generated successfully!")
            st.code(f"""
username: {username}
  email: {email}
  name: {name}
  password: {hashed_password}
""")
            
            # Option to add to config file
            if st.button("Add to config.yaml"):
                config_path = "config.yaml"
                
                if os.path.exists(config_path):
                    with open(config_path) as file:
                        config = yaml.load(file, Loader=SafeLoader)
                    
                    # Add new user
                    if username not in config["credentials"]["usernames"]:
                        config["credentials"]["usernames"][username] = {
                            "email": email,
                            "name": name,
                            "password": hashed_password
                        }
                        
                        # Add to preauthorized emails
                        if email not in config["preauthorized"]["emails"]:
                            config["preauthorized"]["emails"].append(email)
                        
                        with open(config_path, 'w') as file:
                            yaml.dump(config, file, default_flow_style=False)
                        
                        st.success(f"User {username} added to config.yaml!")
                    else:
                        st.error(f"Username {username} already exists in config.yaml!")
                else:
                    st.error("config.yaml not found!")

st.markdown("""
### Instructions
1. Enter a username, name, email, and password
2. Click "Generate Password Hash" to create a secure hash
3. Click "Add to config.yaml" to add the user to the configuration file
4. The default admin account is:
   - Username: admin
   - Password: admin123
""") 