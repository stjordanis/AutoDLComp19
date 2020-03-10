#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time:    2019/9/27 10:12
# @Author:  Mecthew

import tensorflow as tf
from data_process import extract_mfcc_parallel, get_max_length, ohe2cat, pad_seq
from models.attention import Attention
from models.my_classifier import Classifier
from tensorflow.python.keras import optimizers
from tensorflow.python.keras.layers import (
    Activation, LSTM, Dense, Dropout, Flatten, GlobalMaxPool1D, Input, Lambda,
    SpatialDropout1D
)
from tensorflow.python.keras.models import Model as TFModel
from tools import log


class LstmAttention(Classifier):
    def __init__(self):
        # clear_session()
        log("new LSTM")
        self.max_length = None
        self._model = None
        self.is_init = False
        self.epoch_cnt = 0
        self.mfcc_mean, self.mfcc_std = None, None
        self.mel_mean, self.mel_std = None, None
        self.cent_mean, self.cent_std = None, None
        self.stft_mean, self.stft_std = None, None

    def preprocess_data(self, x):
        if self.model_config["common"]["is_cut_audio"]:
            x = [sample[0:self.model_config["common"]["max_audio_duration"] * self.model_config["common"]["audio_sample_rate"]] for sample in x]
        # extract mfcc
        x_mfcc = extract_mfcc_parallel(x,
                                       sr=self.model_config["common"]["sr"],
                                       fft_duration=self.model_config["common"]["fft_duration"],
                                       hop_duration=self.model_config["common"]["hop_duration"],
                                       n_mfcc=self.model_config["common"]["num_mfcc"])
        if self.max_length is None:
            self.max_length = get_max_length(x_mfcc)
            self.max_length = min(self.model_config["common"]["max_frame_num"], self.max_length)
        x_mfcc = pad_seq(x_mfcc, pad_len=self.max_length)

        return x_mfcc

    def init_model(self, input_shape, num_classes, model_config, **kwargs):
        inputs = Input(shape=input_shape)
        lstm_1 = LSTM(128, return_sequences=True)(inputs)
        activation_1 = Activation('tanh')(lstm_1)
        if num_classes >= 20:
            if num_classes < 30:
                dropout1 = SpatialDropout1D(0.5)(activation_1)
                attention_1 = Attention(8, 16)([dropout1, dropout1, dropout1])
            # no dropout to get more infomation for classifying a large number
            # classes
            else:
                attention_1 = Attention(8, 16)([activation_1, activation_1, activation_1])
            k_num = 10
            kmaxpool_l = Lambda(
                lambda x: tf.reshape(
                    tf.nn.top_k(tf.transpose(x, [0, 2, 1]), k=k_num, sorted=True)[0],
                    shape=[-1, k_num, 128]
                )
            )(attention_1)
            flatten = Flatten()(kmaxpool_l)
            dropout2 = Dropout(rate=0.5)(flatten)
        else:
            dropout1 = SpatialDropout1D(0.5)(activation_1)
            attention_1 = Attention(8, 16)([dropout1, dropout1, dropout1])
            pool_l = GlobalMaxPool1D()(attention_1)
            dropout2 = Dropout(rate=0.5)(pool_l)
        dense_1 = Dense(units=256, activation='softplus')(dropout2)
        outputs = Dense(units=num_classes, activation='softmax')(dense_1)

        self.model_config = model_config

        model = TFModel(inputs=inputs, outputs=outputs)
        optimizer = optimizers.Nadam(
            lr=self.model_config["optimizer"]["lr_lstm_attention"],
            beta_1=1-self.model_config["optimizer"]["beta_1"],
            beta_2=1-self.model_config["optimizer"]["beta_2"],
            epsilon=self.model_config["optimizer"]["epsilon"],
            schedule_decay=self.model_config["optimizer"]["schedule_decay"]
        )
        model.compile(
            optimizer=optimizer, loss='sparse_categorical_crossentropy', metrics=['accuracy']
        )
        model.summary()
        self._model = model
        self.is_init = True

    def fit(self, train_x, train_y, validation_data_fit, round_num, **kwargs):
        val_x, val_y = validation_data_fit

        # if train_loop_num == 1:
        #     patience = 2
        #     epochs = 3
        # elif train_loop_num == 2:
        #     patience = 3
        #     epochs = 10
        # elif train_loop_num < 10:
        #     patience = 4
        #     epochs = 16
        # elif train_loop_num < 15:
        #     patience = 4
        #     epochs = 24
        # else:
        #     patience = 8
        #     epochs = 32

        patience = 2
        # epochs = self.epoch_cnt + 3
        epochs = 10
        callbacks = [tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=patience)]

        self._model.fit(
            train_x,
            ohe2cat(train_y),
            epochs=epochs,
            callbacks=callbacks,
            validation_data=(val_x, ohe2cat(val_y)),
            # validation_split=0.2,
            verbose=1,  # Logs once per epoch.
            batch_size=32,
            shuffle=True,
            # initial_epoch=self.epoch_cnt,
            # use_multiprocessing=True
        )
        self.epoch_cnt += 3

    def predict(self, x_test, batch_size=32):
        return self._model.predict(x_test, batch_size=batch_size)