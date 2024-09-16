import paho.mqtt.client as mqtt
import numpy as np
import tensorflow as tf


from sklearn.preprocessing import StandardScaler


model = tf.keras.models.load_model('./best_model/cnn_best_model.h5')


gesture_classes = ['Angry', 'Cheer', 'Clap', 'Come', 'Crazy', 'Facepalm', 'Idle', 'Point', 'Salute', 'ThumbsUp', 'Wave']


data_buffer = []


def on_message(client, userdata, msg):
    global data_buffer  
    try:
        new_data = list(map(float, msg.payload.decode().split()))
        
        if len(new_data) == 21:
            data_buffer.append(new_data)

            if len(data_buffer) > 380:
                data_buffer = data_buffer[-380:]
            elif len(data_buffer) < 380:
                data_buffer.extend([[0] * 21] * (380 - len(data_buffer)))

            input_data = np.array(data_buffer)
            
            scaler = StandardScaler()
            input_data_scaled = scaler.fit_transform(input_data)
            
            input_data_scaled = input_data_scaled.reshape(1, 380, 21)
            
            prediction = model.predict(input_data_scaled)
            predicted_class = np.argmax(prediction, axis=1)[0]
            
            predicted_class_name = gesture_classes[predicted_class]
            print(f'Predicted Gesture Class: {predicted_class_name}')
        
        else:
            print(f'Invalid data length received: {len(new_data)}')
    
    except Exception as e:
        print(f'Error processing message: {e}')


client = mqtt.Client()

client.on_message = on_message


client.connect('localhost', 1883, 60)
client.subscribe('Gesture2Emote')


client.loop_forever()
