import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os


mb_size = 32
X_dim = 784
z_dim = 64
h_dim = 128
lr = 1e-3
d_steps = 3

mnist = input_data.read_data_sets('../../MNIST_data', one_hot=True)


def plot(samples):
    fig = plt.figure(figsize=(4, 4))
    gs = gridspec.GridSpec(4, 4)
    gs.update(wspace=0.05, hspace=0.05)

    for i, sample in enumerate(samples):
        ax = plt.subplot(gs[i])
        plt.axis('off')
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_aspect('equal')
        plt.imshow(sample.reshape(28, 28), cmap='Greys_r')

    return fig


def xavier_init(size):
    in_dim = size[0]
    xavier_stddev = 1. / tf.sqrt(in_dim / 2.)
    return tf.random_normal(shape=size, stddev=xavier_stddev)


def log(x):
    return tf.log(x + 1e-8)


X = tf.placeholder(tf.float32, shape=[None, X_dim])
z = tf.placeholder(tf.float32, shape=[None, z_dim])

D_W1 = tf.Variable(xavier_init([X_dim + z_dim, h_dim]))
D_b1 = tf.Variable(tf.zeros(shape=[h_dim]))
D_W2 = tf.Variable(xavier_init([h_dim, 1]))
D_b2 = tf.Variable(tf.zeros(shape=[1]))

Q_W1 = tf.Variable(xavier_init([X_dim, h_dim]))
Q_b1 = tf.Variable(tf.zeros(shape=[h_dim]))
Q_W2 = tf.Variable(xavier_init([h_dim, z_dim]))
Q_b2 = tf.Variable(tf.zeros(shape=[z_dim]))

P_W1 = tf.Variable(xavier_init([z_dim, h_dim]))
P_b1 = tf.Variable(tf.zeros(shape=[h_dim]))
P_W2 = tf.Variable(xavier_init([h_dim, X_dim]))
P_b2 = tf.Variable(tf.zeros(shape=[X_dim]))

theta_G = [Q_W1, Q_W2, Q_b1, Q_b2, P_W1, P_W2, P_b1, P_b2]
theta_D = [D_W1, D_W2, D_b1, D_b2]


def sample_z(m, n):
    return np.random.uniform(-1., 1., size=[m, n])


def Q(X):
    h = tf.nn.relu(tf.matmul(X, Q_W1) + Q_b1)
    h = tf.matmul(h, Q_W2) + Q_b2
    return h


def P(z):
    h = tf.nn.relu(tf.matmul(z, P_W1) + P_b1)
    h = tf.matmul(h, P_W2) + P_b2
    return tf.nn.sigmoid(h)


def D(X, z):
    inputs = tf.concat([X, z], axis=1)
    h = tf.nn.relu(tf.matmul(inputs, D_W1) + D_b1)
    return tf.nn.sigmoid(tf.matmul(h, D_W2) + D_b2)


z_hat = Q(X)
X_hat = P(z)

with tf.name_scope('fake_image'):
    fake_image = tf.reshape(X_hat, [-1, 28, 28, 1])
    tf.summary.image('fake', fake_image, 32)

D_enc = D(X, z_hat)
D_gen = D(X_hat, z)

D_loss = -tf.reduce_mean(log(D_enc) + log(1 - D_gen))
G_loss = -tf.reduce_mean(log(D_gen) + log(1 - D_enc))
D_enc  = -tf.reduce_mean(log(D_enc))
D_gen  = -tf.reduce_mean(log(D_gen))

with tf.name_scope('loss_result'):
    tf.summary.scalar('d_enc', D_enc)
    tf.summary.scalar('d_gen', D_gen)
    tf.summary.scalar('d_loss', D_loss)
    tf.summary.scalar('g_loss', G_loss)

D_solver = (tf.train.AdamOptimizer(learning_rate=lr)
            .minimize(D_loss, var_list=theta_D))
G_solver = (tf.train.AdamOptimizer(learning_rate=lr)
            .minimize(G_loss, var_list=theta_G))

# Limit GPU usage
gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.333)
config = tf.ConfigProto(gpu_options=gpu_options)
config.gpu_options.allow_growth=True
sess = tf.InteractiveSession(config=config)
sess.run(tf.global_variables_initializer())

# Merge all the summaries and write them out to /tmp/tensorflow/loam/ (by default)
merged = tf.summary.merge_all()
logger = tf.summary.FileWriter('/tmp/tensorflow/ali/', sess.graph)
tf.global_variables_initializer().run()


if not os.path.exists('out/'):
    os.makedirs('out/')

i = 0

for it in range(1000000):
    X_mb, _ = mnist.train.next_batch(mb_size)
    z_mb = sample_z(mb_size, z_dim)

    _, D_loss_curr = sess.run(
        [D_solver, D_loss], feed_dict={X: X_mb, z: z_mb}
    )

    _, G_loss_curr = sess.run(
        [G_solver, G_loss], feed_dict={X: X_mb, z: z_mb}
    )

    if it % 1000 == 0:
        print('Iter: {}; D_loss: {:.4}; G_loss: {:.4}'
              .format(it, D_loss_curr, G_loss_curr))

        summary, samples = sess.run([merged, X_hat], feed_dict={X: X_mb, z: sample_z(32, z_dim)})
        logger.add_summary(summary, it)

logger.close()
