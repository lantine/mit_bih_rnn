#!/usr/bin/env python
from __future__ import print_function

import numpy as np
import cPickle as pickle
import os
import functools
import tensorflow as tf
import sys
from Hlookup import cluster

np.set_printoptions(threshold=np.nan)

script_path = os.path.dirname(os.path.realpath(__file__))

data_path = ''.join([script_path, "/mit_bih.pkl"])

mcmc_train_x_path = ''.join([script_path, "/mcmc_data/mcmc_train_x0.dat"])
mcmc_train_y_path = ''.join([script_path, "/mcmc_data/mcmc_train_y0.dat"])

mcmc_test_x_path = ''.join([script_path, "/mcmc_data/mcmc_test_x1.dat"])
mcmc_test_y_path = ''.join([script_path, "/mcmc_data/mcmc_test_y1.dat"])

if len(sys.argv) > 1:
	_save_path = sys.argv[1]

else:
	_save_path = ''.join([script_path, '/logs/vars/tmp/model.ckpt'])

data_file = open(data_path, 'r')

data = pickle.load(data_file)

data_file.close()

window_length = 10

window_skip = 1

no_features = window_length * len(data[0][0][0])

#Non-patient-specific-training error target from state-of-the-art of 2017: http://ieeexplore.ieee.org/document/7893269/
error_target = 1.0

def feed_windows(_data, _window_skip, _window_len, _features_per_step):
    data_seq = np.zeros((len(_data),_window_len*_features_per_step))
    window_start_index = 0
    window_end_index = window_start_index+_window_len
    in_seq_index = 0
    while window_end_index < len(_data):
        data_window = _data[window_start_index:window_end_index].flatten()
        data_seq[in_seq_index] = data_window
        in_seq_index+=1
        window_start_index+=_window_skip
        window_end_index+=_window_skip
    return data_seq

data_train_or_test = data[2] 

'''
for i in range(len(data_train_or_test)):
	choice = np.random.randint(0,10)
	if choice == 0 and max(data[1][i]) > 0.9 and test_quotas[np.argmax(data[1][i])] > 0:
		data_train_or_test[i] = 1
		test_quotas[np.argmax(data[1][i])]-=1
'''

no_train = len(data_train_or_test)-np.sum(data_train_or_test)
no_test = np.sum(data_train_or_test)

true_data = [[np.zeros((no_train, len(data[0][0]), no_features),dtype=np.float32), np.zeros((no_train, len(data[1][0])),dtype=np.float32)],[np.zeros((no_test, len(data[0][0]), no_features),dtype=np.float32), np.zeros((no_test, len(data[1][0])),dtype=np.float32)]]

print("no_train: ",no_train,"\nno_test: ",no_test)

test_index = 0
train_index = 0

for i in range(len(data_train_or_test)):
	if data_train_or_test[i]:
		true_data[1][0][test_index] = feed_windows(data[0][i],window_skip,window_length,len(data[0][0][0]))
		true_data[1][1][test_index] = data[1][i]
		test_index+=1
	else:
		true_data[0][0][train_index] = feed_windows(data[0][i],window_skip,window_length,len(data[0][0][0]))
                true_data[0][1][train_index] = data[1][i]
                train_index+=1

mcmc_train_x = open(mcmc_train_x_path, "w")
mcmc_train_y = open(mcmc_train_y_path, "w")

mcmc_test_x = open(mcmc_test_x_path, "w")
mcmc_test_y = open(mcmc_test_y_path, "w")


no_samples_written = 0

file_no = 0

mcmc_limit = 10000

for i in range(no_train):
        if no_samples_written+len(data[0][0]) > mcmc_limit:
		mcmc_train_x.close()
		mcmc_train_y.close()
                file_no+=1
		mcmc_train_x_path = ''.join([script_path, "/mcmc_data/mcmc_train_x", str(file_no), ".dat"])
                mcmc_train_y_path = ''.join([script_path, "/mcmc_data/mcmc_train_y", str(file_no), ".dat"])
		mcmc_train_x = open(mcmc_train_x_path, "w")
		mcmc_train_y = open(mcmc_train_y_path, "w")
		no_samples_written = 0
	for j in range(len(data[0][0])):
		if max(true_data[0][0][i][j]) == 0.0:
			break
		for k in range(no_features-1):
			mcmc_train_x.write(str(true_data[0][0][i][j][k]))
			mcmc_train_x.write("\t")
		if max(true_data[0][1][i]) > 0.9:
			mcmc_train_y.write(str(np.float32(np.argmax(true_data[0][1][i]))))
		else:
			mcmc_train_y.write(str(np.float32(len(data[1][0]))))
		mcmc_train_y.write("\n")
		mcmc_train_x.write(str(true_data[0][0][i][j][no_features-1]))
		mcmc_train_x.write("\n")
		no_samples_written+=1

no_samples_written = 0
file_no = 0

for i in range(no_test):
        for j in range(len(data[1][0])):
		if max(true_data[1][0][i][j]) == 0.0:
			break
                for k in range(no_features-1):
                        mcmc_test_x.write(str(true_data[1][0][i][j][k]))
                        mcmc_test_x.write("\t")
                if max(true_data[1][1][i]) > 0.9:
                        mcmc_test_y.write(str(np.float32(np.argmax(true_data[1][1][i]))))
                else:
                        mcmc_test_y.write(str(np.float32(len(data[1][0]))))
                mcmc_test_y.write("\n")
                mcmc_test_x.write(str(true_data[1][0][i][j][no_features-1]))
                mcmc_test_x.write("\n")

mcmc_train_x.close()
mcmc_train_y.close()
mcmc_test_x.close()
mcmc_test_y.close()

def lazy_property(function):
    attribute = '_' + function.__name__

    @property
    @functools.wraps(function)
    def wrapper(self):
        if not hasattr(self, attribute):
            setattr(self, attribute, function(self))
        return getattr(self, attribute)
    return wrapper

class VariableSequenceClassification:

    def __init__(self, data, target, num_hidden=150, num_layers=2, num_fc=2, fc_len=20):
        self.data = data
        self.target = target
        self._num_hidden = num_hidden
        self._num_layers = num_layers
        self._num_fc = num_fc
        self._fc_len = fc_len
        self.prediction
        self.error
        self.optimize

    @lazy_property
    def length(self):
        used = tf.sign(tf.reduce_max(tf.abs(self.data), axis=2))
        length = tf.reduce_sum(used, axis=1)
        length = tf.cast(length, tf.int32)
        return length

    @lazy_property
    def prediction(self):
        subcells = []
        for i in range(self._num_layers):
                if i == 0 and self._num_layers > 1:
                    #Dropout added below LSTM layer only, in accordance with http://ieeexplore.ieee.org/document/7333848/?reload=true
                    subcells.append(tf.nn.rnn_cell.DropoutWrapper(tf.nn.rnn_cell.LSTMCell(self._num_hidden, initializer=tf.contrib.layers.xavier_initializer()), input_keep_prob = 0.8))
                else:
                    subcells.append(tf.nn.rnn_cell.LSTMCell(self._num_hidden, initializer = tf.contrib.layers.xavier_initializer()))
        main_cell = tf.nn.rnn_cell.MultiRNNCell(subcells, state_is_tuple=True)
        # Recurrent network.
        output, _ = tf.nn.dynamic_rnn(
            main_cell,
            self.data,
            dtype=tf.float32,
            sequence_length=self.length,
        )
        last = self._last_relevant(output, self.length)
        if self._num_fc == 0:
            last_before_softmax = last
            out_num = self._num_hidden
        else:
            fc_layers = []
            if self._num_fc == 1:
                fc_layers.append(tf.contrib.layers.fully_connected(last, self._fc_len))
            else:
                fc_layers.append(tf.contrib.layers.fully_connected(last, self._fc_len, activation_fn=tf.nn.sigmoid))
                for l in range(1, self._num_fc-1):
                    fc_layers.append(tf.contrib.layers.fully_connected(fc_layers[l-1], self._fc_len, activation_fn=tf.nn.sigmoid))
                fc_layers.append(tf.contrib.layers.fully_connected(fc_layers[self._num_fc-2], self._fc_len))
            last_before_softmax = fc_layers[self._num_fc-1]
            out_num = self._fc_len
                
        # Softmax layer.
        weight, bias = self._weight_and_bias(
            out_num, int(self.target.get_shape()[1]))
        prediction = tf.nn.softmax(tf.matmul(last_before_softmax, weight) + bias)
	prediction = tf.clip_by_value(prediction, 1e-3, 1.0-1e-3)
        return prediction

    @lazy_property
    def cost(self):
        cross_entropy = -tf.reduce_sum(self.target * tf.log(self.prediction))
        return cross_entropy

    @lazy_property
    def optimize(self):
        learning_rate = 0.01
	momentum = 0.0
        optimizer = tf.train.RMSPropOptimizer(learning_rate)
        return optimizer.minimize(self.cost)

    @lazy_property
    def error(self):
        mistakes = tf.not_equal(
            tf.argmax(self.target, 1), tf.argmax(self.prediction, 1))
	#print("Mistakes: ",mistakes)
        return tf.reduce_mean(tf.cast(mistakes, tf.float32))

    @staticmethod
    def _weight_and_bias(in_size, out_size):
	#weight = tf.truncated_normal([in_size, out_size], stddev=0.01)
        weight = tf.get_variable("weight", shape=[in_size,out_size], initializer=tf.contrib.layers.xavier_initializer())
        bias = tf.constant(0.1, shape=[out_size], dtype=tf.float32)
        return weight, tf.Variable(bias)

    @staticmethod
    def _last_relevant(output, length):
        batch_size = tf.shape(output)[0]
        max_length = int(output.get_shape()[1])
        output_size = int(output.get_shape()[2])
        index = tf.range(0, batch_size) * max_length + (length - 1)
        flat = tf.reshape(output, [-1, output_size])
        relevant = tf.gather(flat, index)
        return relevant




if __name__ == '__main__':
    # We treat images as sequences of pixel rows.
    all_data = true_data
    train = all_data[0]
    test = all_data[1]
    conf_weights =  np.sum(test[1], axis=0)
    batch_size = 200
    no_examples, rows, row_size = train[0].shape
    num_classes = len(train[1][0])
    no_batches = no_examples/batch_size
    data = tf.placeholder(tf.float32, [None, rows, row_size])
    target = tf.placeholder(tf.float32, [None, num_classes])
    model = VariableSequenceClassification(data, target)
    sess = tf.Session()
    sess.run(tf.global_variables_initializer())

    print(test[0].shape,test[1].shape)
    saver = tf.train.Saver() 
    for epoch in range(400):
        error_sum = 0.0 
        for i in range(no_batches):
            batch_data = train[0][i*batch_size:(i+1)*batch_size]
            batch_target = train[1][i*batch_size:(i+1)*batch_size]
            sess.run(model.optimize, feed_dict={data: batch_data, target: batch_target})
            train_error = sess.run(model.error, feed_dict={data:batch_data, target: batch_target})
            print('Epoch {:2d} train batch {:2d} error {:3.1f}%'.format(epoch+1, i+1, 100*train_error))
            error_sum+=100*train_error
            pred=sess.run(model.prediction,feed_dict={data: batch_data, target: batch_target})
            #print("pred: ", pred)
            #print("pred-batch_target: ",pred-batch_target)
        if (epoch+1)%5 == 0 or error_sum/no_batches <= error_target:
            save_path = saver.save(sess, _save_path, global_step=epoch)
            print("Model vars saved in file: %s" % save_path)
        if error_sum/no_batches <= error_target:
            break
	'''
	test_pred = sess.run(model.prediction,feed_dict={data:test[0], target: test[1]})
	test_pred_int = np.zeros((len(test_pred)),dtype=np.int32)
	test_pred_targets = np.zeros((len(test_pred)),dtype=np.int32)
	test_pred_weights = np.zeros((len(test_pred)),dtype=np.int32)
	for x in range(len(test_pred)):
		class_int = np.argmax(test_pred[x])
		target_int = np.argmax(test[1][x])
		test_pred_int[x] = class_int
		test_pred_targets[x] = target_int
		test_pred_weights[x] = int(conf_weights[class_int])
	conf_mat = tf.contrib.metrics.confusion_matrix(
		tf.convert_to_tensor(test_pred_targets,dtype=tf.int32),
		tf.convert_to_tensor(test_pred_int,dtype=tf.int32),
		num_classes = 14,
		weights = tf.convert_to_tensor(test_pred_weights,dtype=tf.int32))
	print('Confusion matrix:\n',conf_mat)
	variables_names = [v.name for v in tf.trainable_variables()]
	values = sess.run(variables_names)
	print('Trainable variable values:')
	for k, v in zip(variables_names, values):
		print (k, v)
	'''