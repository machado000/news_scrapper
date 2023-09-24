

Selenium requirements

- install Google Chrome
```
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
google-chrome-stable -version
```

- install chromedriver
```
https://googlechromelabs.github.io/chrome-for-testing/#stable
wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/117.0.5938.92/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
cp ./chromedriver-linux64/chromedriver /usr/bin/
chromedriver -version
```
