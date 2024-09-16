### Gesture2Emote

AIDL02 Assignment Submission

- _MAIN notebook_: Gesture2Emotev2.ipynb
- _LOSOCV/Generalization test notebook_: Gesture2Emote_LOSO.ipynb  
  Colab versions also provided (What's different is ".h5" -> ".keras" and importing of data from GDrive)

- _Gesture2Emote Dataset_: https://drive.google.com/drive/folders/1TrKwWwzATh3Btyf0yx7kHm2Qas0zDumw?usp=sharing

- _Deployment_:  
  MQTT Receiver + model tester: G2E_mqtt.py  
  Awinda IMU MQTT Publisher: awindareader_server_g2e.py (+ mtwinfo_g2e.py)
