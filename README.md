# tcp-keepalives
Fork of https://github.com/cloudflare/cloudflare-blog/tree/master/2019-09-tcp-keepalives

see related blog by cloudflare

* https://blog.cloudflare.com/when-tcp-sockets-refuse-to-die/
* https://blog.cloudflare.com/syn-packet-handling-in-the-wild/
* https://blog.cloudflare.com/this-is-strictly-a-violation-of-the-tcp-specification/
* https://blog.cloudflare.com/the-story-of-one-latency-spike/

written by me

* qiita

# Testing TCP Keepalives on Linux

### ENVIRONMENT TESTED
All of the setting of TCP below is default.

```
# Kernel 4.19.121
# uname -a
Linux b441e0a92c23 4.19.121-linuxkit #1 SMP Thu Jan 21 15:36:34 UTC 2021 x86_64 x86_64 x86_64 GNU/Linux

# Ubuntu 16.04.7 LTS
# cat /etc/os-release
NAME="Ubuntu"
VERSION="16.04.7 LTS (Xenial Xerus)"
..

# SYN retry count
# You can overwrite by setsockopt(sd, IPPROTO_TCP, TCP_SYNCNT, 6);
# sysctl net.ipv4.tcp_syn_retries
net.ipv4.tcp_syn_retries = 6

# SYN+ACK retry count
root@b441e0a92c23:~/go/src/etc/tcp-keepalives# sysctl net.ipv4.tcp_synack_retries
net.ipv4.tcp_synack_retries = 5

# TCP KEEPALIVE
# sysctl -a | grep tcp_keepalive
# Send first keepalive probe after 7200 seconds of idleness.
# You can overwrite by setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 7200)
net.ipv4.tcp_keepalive_time = 7200

# Send subsequent keepalive probes after 75 seconds
# You can overwrite by setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 75)
net.ipv4.tcp_keepalive_intvl = 75

# Time out after 9 failed probes.
# You can overwrite by setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
net.ipv4.tcp_keepalive_probes = 9

# Data packet or  window probes is retransmitted 15 times
# sysctl net.ipv4.tcp_retries2
net.ipv4.tcp_retries2 = 15

# This specifies how many seconds to wait for a final FIN packet before the socket is forcibly closed. In other words, timeout seconds from FIN-WAIT-2 to CLOSED
# This does NOT control TIME-WAIT. Timeout from TIME-WAIT to CLOSED is 2 * MSL(Maximum Segment Lifetime), and is hard coded at kernel as 60 seconds.
# sysctl net.ipv4.tcp_fin_timeout
net.ipv4.tcp_fin_timeout = 60

```


`tcp-dead.py`

Shows packets retransmissions when user sends data over dead,
previously idle connection.

`tcp-estab.py`

Proves that TCP_USER_TIMEOUT doesn't affect idle socket, even if first
transmitted packet is lost. In other words, in the case of idle socket
TCP_USER_TIMEOUT measures delay not from last-good packet, but from
the moments the retransmissions begun.

### `test-syn-sent.py`
パケットがdropされるよう意図的に設定した状態で、`connect`を呼ぶ。サーバ側はパケットを全く受け取らない。

本来は6回retryされ7回目のタイミングでタイムアウトするが4回しかretryされていない。謎だがおそらくこれはバグで、元ブログは6回されて、2分10秒後にタイムアウトしていた。そちらが正しい挙動。

TCP_USER_TIMEOUTはtimerにかかわらず適用される。5秒に設定した場合、7秒の再送のタイミングではなく、5秒経過時にタイムアウトする。

```
 00:00:00.000000 IP 127.0.0.1.49318 > 127.0.0.1.1: Flags [S], seq 1376001677, win 65495, options [mss 65495,sackOK,TS val 2218095156 ecr 0,nop,wscale 7], length 0
 00:00:01.021144 IP 127.0.0.1.49318 > 127.0.0.1.1: Flags [S], seq 1376001677, win 65495, options [mss 65495,sackOK,TS val 2218096177 ecr 0,nop,wscale 7], length 0
 00:00:03.071705 IP 127.0.0.1.49318 > 127.0.0.1.1: Flags [S], seq 1376001677, win 65495, options [mss 65495,sackOK,TS val 2218098228 ecr 0,nop,wscale 7], length 0
 00:00:07.099018 IP 127.0.0.1.49318 > 127.0.0.1.1: Flags [S], seq 1376001677, win 65495, options [mss 65495,sackOK,TS val 2218102255 ecr 0,nop,wscale 7], length 0
 00:00:15.290777 IP 127.0.0.1.49318 > 127.0.0.1.1: Flags [S], seq 1376001677, win 65495, options [mss 65495,sackOK,TS val 2218110447 ecr 0,nop,wscale 7], length 0
[Errno 110] Connection timed out
[ ] SO_ERROR = 0
[ ] connect took 31.649053s
```

nonblockingにて`connect`し、その後`poll.register(c, select.POLLOUT)`後に`poll.poll()`した場合で間には以下のようになる。`ss`の出力を一部出力。

nonblockingで`connect`してすぐ戻っても、裏側でTCPのフローは続いていることがわかる。


```
 00:00:00.000000 IP 127.0.0.1.50196 > 127.0.0.1.1: Flags [S], seq 922391137, win 65495, options [mss 65495,sackOK,TS val 2218533434 ecr 0,nop,wscale 7], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
SYN-SENT   0      1      127.0.0.1:50196              127.0.0.1:1                   timer:(on,995ms,0)

 00:00:01.012009 IP 127.0.0.1.50196 > 127.0.0.1.1: Flags [S], seq 922391137, win 65495, options [mss 65495,sackOK,TS val 2218534446 ecr 0,nop,wscale 7], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
SYN-SENT   0      1      127.0.0.1:50196              127.0.0.1:1                   timer:(on,1.999ms,1)

 00:00:03.030395 IP 127.0.0.1.50196 > 127.0.0.1.1: Flags [S], seq 922391137, win 65495, options [mss 65495,sackOK,TS val 2218536498 ecr 0,nop,wscale 7], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
SYN-SENT   0      1      127.0.0.1:50196              127.0.0.1:1                   timer:(on,3.041ms,2)

 00:00:07.061180 IP 127.0.0.1.50196 > 127.0.0.1.1: Flags [S], seq 922391137, win 65495, options [mss 65495,sackOK,TS val 2218540529 ecr 0,nop,wscale 7], length 0
 00:00:15.255837 IP 127.0.0.1.50196 > 127.0.0.1.1: Flags [S], seq 922391137, win 65495, options [mss 65495,sackOK,TS val 2218548724 ecr 0,nop,wscale 7], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              

[ ] SO_ERROR = 110
[ ] connect took 31.616817s
```

### `test-syn-recv.py`
サーバからのパケットがdropされるよう意図的に設定した状態で、クライアントがnonblockingで`connect`してすぐにcloseする。

クライアントはFIN/RSTなにも送らず消える。ESTABLISHEDになっていないので当然である。

サーバはSYN-RECVのまま残るが、５回再送してFIN/RSTなにも送らず消える。
TCP_USER_TIMEOUTは全く影響しない。

```
 00:00:00.000000 IP 127.0.0.1.55776 > 127.0.0.1.1: Flags [S], seq 2139370685, win 65495, options [mss 65495,sackOK,TS val 2221325097 ecr 0,nop,wscale 7], length 0
 00:00:00.000046 IP 127.0.0.1.1 > 127.0.0.1.55776: Flags [S.], seq 1728156958, ack 2139370686, win 65483, options [mss 65495,sackOK,TS val 2221325097 ecr 2221325097,nop,wscale 7], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:55776               timer:(on,995ms,0)

 00:00:00.999640 IP 127.0.0.1.1 > 127.0.0.1.55776: Flags [S.], seq 1728156958, ack 2139370686, win 65483, options [mss 65495,sackOK,TS val 2221326130 ecr 2221325097,nop,wscale 7], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:55776               timer:(on,1.016ms,1)

 00:00:03.049032 IP 127.0.0.1.1 > 127.0.0.1.55776: Flags [S.], seq 1728156958, ack 2139370686, win 65483, options [mss 65495,sackOK,TS val 2221328180 ecr 2221325097,nop,wscale 7], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:55776               timer:(on,3.057ms,2)

1s/3s/7s/15s/31s後に再送され、64s後のタイミングでSYN-RECVが消える
.
.
.

State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:55776               timer:(on,1.629ms,5)

State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  

```

なお、クライアントの`close`をコメントアウトすると、
以下のようにSYN-SENTとSYN-RECVのまま残り、お互いが再送をつづけ両方とも最終的にタイムアウトする。


```
 00:00:15.429482 IP 127.0.0.1.1 > 127.0.0.1.56546: Flags [S.], seq 805156047, ack 431034407, win 65483, options [mss 65495,sackOK,TS val 2221724148 ecr 2221708684,nop,wscale 7], length 0
 00:00:15.429500 IP 127.0.0.1.56546 > 127.0.0.1.1: Flags [S], seq 431034406, win 65495, options [mss 65495,sackOK,TS val 2221724148 ecr 0,nop,wscale 7], length 0
 00:00:15.429540 IP 127.0.0.1.1 > 127.0.0.1.56546: Flags [S.], seq 805156047, ack 431034407, win 65483, options [mss 65495,sackOK,TS val 2221724148 ecr 2221708684,nop,wscale 7], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
SYN-SENT   0      1      127.0.0.1:56546              127.0.0.1:1                   timer:(on,15sec,4)
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:56546               timer:(on,15sec,8)

```

### `test-syn-ack.py`
サーバは`listen`だけして`accept`しない。

クライアントは`connect`をnonblockingにて行い、8秒後に`write`する。

この場合普通に8秒後に以下になり、正常終了する。LISTENにaccept待ち1あり、11バイトがサーバの受信バッファにたまっていることがわかる。

```
 00:00:08.047951 IP 127.0.0.1.34252 > 127.0.0.1.1: Flags [P.], seq 1:12, ack 1, win 512, options [nop,nop,TS val 2224684735 ecr 2224676687], length 11
 00:00:08.047980 IP 127.0.0.1.1 > 127.0.0.1.34252: Flags [.], ack 12, win 512, options [nop,nop,TS val 2224684735 ecr 2224684735], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:34252              127.0.0.1:1                  
ESTAB      11     0      127.0.0.1:1                  127.0.0.1:34252              

```

上記をSYN->SYNACK->ACKの流れでクライアントからの最後のACKのみパケット破棄するようにする。

クライアントはACKを返してすぐにESTABLISHEDになる。

サーバからみれば`test-syn-recv.py`と全く同じ状況のため、同じように再送する。原因は`test-syn-recv.py`と異なるがサーバは知る由もないので当然同じ挙動になる。

タイムアウト前にクライアントからデータが届いた場合、正常にACKを受け取った場合と同じように正常にESTABLISHEDに移行する。 

```
 # ここまでは`test-syn-recv.py`と同様でサーバは1s/3s/7sと再送する
 00:00:07.056506 IP 127.0.0.1.1 > 127.0.0.1.34920: Flags [S.], seq 1519725190, ack 3330746295, win 65483, options [mss 65495,sackOK,TS val 2225017902 ecr 2225010812,nop,wscale 7], length 0
 00:00:07.056578 IP 127.0.0.1.34920 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2225017902 ecr 2225010812], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:34920              127.0.0.1:1                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:34920               timer:(on,7.043ms,3)

[x] send
 00:00:08.016074 IP 127.0.0.1.34920 > 127.0.0.1.1: Flags [P.], seq 1:12, ack 1, win 512, options [nop,nop,TS val 2225018862 ecr 2225010812], length 11
 00:00:08.016122 IP 127.0.0.1.1 > 127.0.0.1.34920: Flags [.], ack 12, win 512, options [nop,nop,TS val 2225018862 ecr 2225018862], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:34920              127.0.0.1:1                  
ESTAB      11     0      127.0.0.1:1                  127.0.0.1:34920              

State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:34920              127.0.0.1:1                  
ESTAB      11     0      127.0.0.1:1                  127.0.0.1:34920              
```

### `test_accept_defer.py`

TCP_DEFER_ACCEPTを指定したパターンを考える。

TCP_DEFER_ACCEPTとはそもそも何かというと、クライアントからのACKを受け取ってもSYNキューからACCEPTキューに移動せずにSYN-RECVの状態のままにし、クライアントからデータが転送されたときにACCEPTキューに移動しESTABLISHEDにする仕組みである。これによりアプリケーションが`accept`したタイミングでブロッキングせずに即時に`read`できる。

ただし、指定した秒数経過すると通常の挙動と等しくなり、ACKが受け取れていない(実際には過去に受け取れているが捨てている)ことによるSYNACKの再送を行い始める。この場合はアプリケーションがすぐに`read`できるとは限らない。

see: http://blog.yuryu.jp/2014/05/tcp-defer-accept.html


ここでは、`test-syn-ack.py`と同様に8秒sleep後データを送るとするが、サーバ側はTCP_DEFER_ACCEPTを10秒に設定している。パケットは問題なく疎通可能。

以下のように8秒後にデータを受信するまでSYNーRECVであることがわかる。また、それまでサーバは一切SYNACKの再送をしていない。古いカーネルは通常のACKを受け取れていない場合と同様に再送をしていたようだが指定秒数（ここでは10秒）経過するまで送らないような制御が入っているようである。timerは都度起動されているよう(再送回数カウンタはずっとゼロのまま)なのでtimerで起こされたタイミングで経過したか否かをみているのではと思われる。

また、データを受け取るまでは、SYNキューに入っておりACCEPTキューにはないのでLISTENのRECV-Qは0である。


```
 00:00:00.000000 IP 127.0.0.1.40064 > 127.0.0.1.1: Flags [S], seq 3237880505, win 65495, options [mss 65495,sackOK,TS val 2227584692 ecr 0,nop,wscale 7], length 0
 00:00:00.000064 IP 127.0.0.1.1 > 127.0.0.1.40064: Flags [S.], seq 2417292221, ack 3237880506, win 65483, options [mss 65495,sackOK,TS val 2227584692 ecr 2227584692,nop,wscale 7], length 0
 00:00:00.000111 IP 127.0.0.1.40064 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2227584692 ecr 2227584692], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:40064              127.0.0.1:1                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:40064               timer:(on,996ms,0)

State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:40064              127.0.0.1:1                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:40064               timer:(on,1.009ms,0)

State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:40064              127.0.0.1:1                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:40064               timer:(on,3.049ms,0)

State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:40064              127.0.0.1:1                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:40064               timer:(on,1.036ms,0)

State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:40064              127.0.0.1:1                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:40064               timer:(on,7.055ms,0)

[x] send
 00:00:08.048083 IP 127.0.0.1.40064 > 127.0.0.1.1: Flags [P.], seq 1:12, ack 1, win 512, options [nop,nop,TS val 2227592740 ecr 2227584692], length 11
 00:00:08.048155 IP 127.0.0.1.1 > 127.0.0.1.40064: Flags [.], ack 12, win 512, options [nop,nop,TS val 2227592740 ecr 2227592740], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:40064              127.0.0.1:1                  
ESTAB      11     0      127.0.0.1:1                  127.0.0.1:40064              

```

ここでデータを送るタイミングを8秒->20秒にしてみる。
1s/3s/7s/15s/31sと続くtimerの中でTCP_DEFER_ACCEPT10秒であることより、15秒後のタイミングでSYNACKを飛ばしESTABLISHEDになっていることがわかる。

この場合、アプリケーションから見るとデータが`read`できるまで10秒かかることになる。

```
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
SYN-RECV   0      0      127.0.0.1:1                  127.0.0.1:42326               timer:(on,1.071ms,0)
ESTAB      0      0      127.0.0.1:42326              127.0.0.1:1                  

 00:00:15.337369 IP 127.0.0.1.1 > 127.0.0.1.42326: Flags [S.], seq 1608862908, ack 2781673925, win 65483, options [mss 65495,sackOK,TS val 2228729332 ecr 2228713995,nop,wscale 7], length 0
 00:00:15.337427 IP 127.0.0.1.42326 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2228729332 ecr 2228713994], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:1                  127.0.0.1:42326              
ESTAB      0      0      127.0.0.1:42326              127.0.0.1:1        
.
.
この後10秒後にデータが送られる

```

### `test_idle.py`
ESTABLISHEDになってすぐにパケットが届かないように意図的に設定する。クライアントのsocketのtcpkeepaliveの設定は以下になっている。

* SO_KEEPALIVE = 1 - Let's enable keepalives.
* TCP_KEEPIDLE = 5 - Send first keepalive probe after 5 seconds of idleness.
* TCP_KEEPINTVL = 3 - Send subsequent keepalive probes after 3 seconds.
* TCP_KEEPCNT = 3 - Time out after three failed probes.

5s/8s/11sとパケットを送り、14sにタイムアウト判定している。このとき、RSTをとばしている。

timerはkeepaliveと表示されている。


```
 00:00:00.000000 IP 127.0.0.1.59250 > 127.0.0.1.1: Flags [S], seq 3260833886, win 65495, options [mss 65495,sackOK,TS val 2251268188 ecr 0,nop,wscale 7], length 0
 00:00:00.000053 IP 127.0.0.1.1 > 127.0.0.1.59250: Flags [S.], seq 2070019716, ack 3260833887, win 65483, options [mss 65495,sackOK,TS val 2251268188 ecr 2251268188,nop,wscale 7], length 0
 00:00:00.000140 IP 127.0.0.1.59250 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2251268188 ecr 2251268188], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:1                  127.0.0.1:59250              
ESTAB      0      0      127.0.0.1:59250              127.0.0.1:1                   timer:(keepalive,2.986ms,0)

 00:00:04.977306 IP 127.0.0.1.59250 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2251273199 ecr 2251268188], length 0
 00:00:07.984276 IP 127.0.0.1.59250 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2251276207 ecr 2251268188], length 0
 00:00:10.992395 IP 127.0.0.1.59250 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2251279215 ecr 2251268188], length 0
 00:00:14.001676 IP 127.0.0.1.59250 > 127.0.0.1.1: Flags [R.], seq 1, ack 1, win 512, options [nop,nop,TS val 2251282222 ecr 2251268188], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:1                  127.0.0.1:59250              

[ ] SO_ERROR = 110
[ ] took: 14.003819 seconds

```

ブログのまとめのような内容になってしまうが、注意点を列挙する。

* keepaliveが起動するためには送信バッファが空である必要がある。
* TCP_USER_TIMEOUTと同時に指定された場合について
  * keepaliveのtimerのタイミングにて、初回でなければTCP_USER_TIMEOUTのチェックが走り、経過していたらタイムアウトさせる
  * TCP_KEEPCNTは完全に無視される。

5s/8s/11s/14sと送る場合、TCP_USER_TIMEOUT=3sであった場合には8sのタイミングでタイムウトする。

5s/8s/11s/14sと送る場合、TCP_USER_TIMEOUT=10sであった場合には11sのタイミングでタイムウトする。

また、

* pollではなく、readだった場合、同様に、ETIMEDOUT(Connection timed out)
* pollでtimeoutした後writeした場合、[EPIPE] Broken pipe

### `test-pacing.py`
サーバは`s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)`にて受信バッファを制限し、accept後すぐ`x.shutdown(socket.SHUT_WR)`にてFINをとばす。readしないのでバッファに溜まるのみ。

クライアントはループで`c.send(b"A" * 16384 * 4)`するが、13回write後ブロックされる。これはクライアントの送信バッファが一杯であるからである。その後クライアントはcloseするが、closeはブロックされずにすぐに返る。だが、送信バッファが一杯であるため、FINがとぶことはない。この挙動はshutdown(socket.SHUT_WR)でも同様。

クライアントは5,6分window probesを送り続けてFIN/RSTとばさずにそのまま消える。サーバはFIN-WAIT-2のまま


以下ログ
```
 00:00:00.000000 IP 127.0.0.1.47400 > 127.0.0.1.1: Flags [S], seq 1951719682, win 1152, options [mss 65495,sackOK,TS val 1760361331 ecr 0,nop,wscale 0], length 0
 00:00:00.000063 IP 127.0.0.1.1 > 127.0.0.1.47400: Flags [S.], seq 1744299355, ack 1951719683, win 1152, options [mss 65495,sackOK,TS val 1760361331 ecr 1760361331,nop,wscale 0], length 0
 00:00:00.000109 IP 127.0.0.1.47400 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 1760361331 ecr 1760361331], length 0
 00:00:00.000497 IP 127.0.0.1.1 > 127.0.0.1.47400: Flags [F.], seq 1, ack 1, win 1152, options [nop,nop,TS val 1760361332 ecr 1760361331], length 0
 00:00:00.000627 IP 127.0.0.1.47400 > 127.0.0.1.1: Flags [.], seq 1:577, ack 2, win 1151, options [nop,nop,TS val 1760361332 ecr 1760361332], length 576
 00:00:00.000662 IP 127.0.0.1.1 > 127.0.0.1.47400: Flags [.], ack 577, win 576, options [nop,nop,TS val 1760361332 ecr 1760361332], length 0
 00:00:00.000700 IP 127.0.0.1.47400 > 127.0.0.1.1: Flags [P.], seq 577:1153, ack 2, win 1151, options [nop,nop,TS val 1760361332 ecr 1760361332], length 576
[s] send_cnt=1
.
.
[s] send_cnt=12
[s] send_cnt=13
[s] notsent before=814464
 00:00:00.042052 IP 127.0.0.1.1 > 127.0.0.1.47400: Flags [.], ack 1153, win 0, options [nop,nop,TS val 1760361373 ecr 1760361332], length 0
# 以降window probesのみ
.
.
 00:00:26.900052 IP 127.0.0.1.47400 > 127.0.0.1.1: Flags [.], ack 2, win 1151, options [nop,nop,TS val 1760388265 ecr 1760374956], length 0
 00:00:26.900341 IP 127.0.0.1.1 > 127.0.0.1.47400: Flags [.], ack 1153, win 0, options [nop,nop,TS val 1760388266 ecr 1760361332], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
LAST-ACK   1      814465 127.0.0.1:47400              127.0.0.1:1                   timer:(persist,23sec,0)
FIN-WAIT-2 1152   0      127.0.0.1:1                  127.0.0.1:47400              
.
.
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
LAST-ACK   1      814465 127.0.0.1:47400              127.0.0.1:1                   timer:(persist,3.036ms,0)
FIN-WAIT-2 1152   0      127.0.0.1:1                  127.0.0.1:47400              

# 開始から5分半ほど経過した11回目の再送のタイミングで再送せずにFIN/RST何もとばさずにクライアントは消える。
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
LAST-ACK   1      814465 127.0.0.1:47400              127.0.0.1:1                   timer:(persist,,0)
FIN-WAIT-2 1152   0      127.0.0.1:1                  127.0.0.1:47400              
# サーバはずっと残る。x.shutdown(socket.SHUT_WR)のみしているため
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
FIN-WAIT-2 1152   0      127.0.0.1:1                  127.0.0.1:47400              
.
.
```

### `test-pacing2.py`
サーバ側は`x.shutdown(socket.SHUT_WR)`せずにゆっくりreadする。この場合、緩やかにクライアント、サーバが通信を行い続ける。

### `test-pacing3.py`
サーバ側は`x.shutdown(socket.SHUT_WR)`せずにreadするが、その前にsleepを挟むことでクライアントがcloseした後にreadを行うことになる。
この場合、クライアントのバッファにあるものを送信しおわってからFINが飛ぶことが確認できる。

遅延して送られたFINに対してのACKを受け取り、FIN-WAIT-2にクライアントは移行し、60秒のタイマー後CLOSEDになる。これはクライアントがcloseをコールしており、いくつかのOS実装ではタイマーが起動されるような実装になっているためである。
https://blog.cloudflare.com/this-is-strictly-a-violation-of-the-tcp-specification/

以下ログ

```
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
FIN-WAIT-1 0      14977  127.0.0.1:53284              127.0.0.1:1                   timer:(persist,122ms,0)
ESTAB      768    0      127.0.0.1:1                  127.0.0.1:53284              
.
.
 00:01:00.719467 IP 127.0.0.1.53284 > 127.0.0.1.1: Flags [P.], seq 814465:815041, ack 1, win 1152, options [nop,nop,TS val 1763364704 ecr 1763364704], length 576
 00:01:00.762295 IP 127.0.0.1.1 > 127.0.0.1.53284: Flags [.], ack 815041, win 576, options [nop,nop,TS val 1763364746 ecr 1763364704], length 0
 00:01:00.821502 IP 127.0.0.1.1 > 127.0.0.1.53284: Flags [.], ack 815041, win 1152, options [nop,nop,TS val 1763364805 ecr 1763364704], length 0
 00:01:00.821582 IP 127.0.0.1.53284 > 127.0.0.1.1: Flags [FP.], seq 815041:815617, ack 1, win 1152, options [nop,nop,TS val 1763364806 ecr 1763364805], length 576
 00:01:00.822959 IP 127.0.0.1.1 > 127.0.0.1.53284: Flags [.], ack 815618, win 575, options [nop,nop,TS val 1763364806 ecr 1763364806], length 0
# バッファ内のものを送信しきっている。
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
FIN-WAIT-2 0      0      127.0.0.1:53284              127.0.0.1:1                   timer:(timewait,55sec,0)
CLOSE-WAIT 0      0      127.0.0.1:1                  127.0.0.1:53284              
.
.
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
FIN-WAIT-2 0      0      127.0.0.1:53284              127.0.0.1:1                   timer:(timewait,661ms,0)
CLOSE-WAIT 0      0      127.0.0.1:1                  127.0.0.1:53284              

State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
CLOSE-WAIT 0      0      127.0.0.1:1                  127.0.0.1:53284 

```

### `test-zero.py`

`test-pacing.py`とだいたい同じ。サーバはacceptだけしてreadしない(acceptしなくても動作は同じではある。厳密にいうとssコマンドLISTENのRECV-Q=1になる点のみが差異)。
クライアントからの送信はサーバの受信バッファが少ないためにすぐにwindow blobesを送りつづけるが、途中でiptableにより意図的にパケットを破棄するようにしてしまう。

その結果window probesに対するackが返却されなくなる。

クライアントは15分window probesを送り続けてFIN/RSTとばさずにそのまま消える。サーバはESTABLISHEDのまま

TCP_USER_TIMEOUTを60秒に設定すると1分47秒後に意図通りタイムアウトした。

```
 00:00:00.000000 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [S], seq 2324904933, win 1152, options [mss 65495,sackOK,TS val 2204487230 ecr 0,nop,wscale 0], length 0
 00:00:00.000027 IP 127.0.0.1.1 > 127.0.0.1.59960: Flags [S.], seq 1031583397, ack 2324904934, win 1152, options [mss 65495,sackOK,TS val 2204487230 ecr 2204487230,nop,wscale 0], length 0
 00:00:00.000049 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204487230 ecr 2204487230], length 0
[ ] c.send()
 00:00:00.204854 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], seq 1:577, ack 1, win 1152, options [nop,nop,TS val 2204487435 ecr 2204487230], length 576
 00:00:00.204869 IP 127.0.0.1.1 > 127.0.0.1.59960: Flags [.], ack 577, win 576, options [nop,nop,TS val 2204487435 ecr 2204487435], length 0
 00:00:00.204880 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [P.], seq 577:1153, ack 1, win 1152, options [nop,nop,TS val 2204487435 ecr 2204487435], length 576
 00:00:00.248436 IP 127.0.0.1.1 > 127.0.0.1.59960: Flags [.], ack 1153, win 0, options [nop,nop,TS val 2204487478 ecr 2204487435], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      129920 127.0.0.1:59960              127.0.0.1:1                   timer:(persist,042ms,0)
ESTAB      1152   0      127.0.0.1:1                  127.0.0.1:59960              

delivered, acked 1152
in-flight: 0
in queue, not in flight: 129920
 00:00:00.458496 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204487688 ecr 2204487478], length 0
 00:00:00.874722 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204488104 ecr 2204487478], length 0
 00:00:01.712590 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204488942 ecr 2204487478], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      129920 127.0.0.1:59960              127.0.0.1:1                   timer:(persist,922ms,3)
ESTAB      1152   0      127.0.0.1:1                  127.0.0.1:59960              

 00:00:03.376701 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204490606 ecr 2204487478], length 0
 00:00:06.704657 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204493934 ecr 2204487478], length 0
 00:00:13.836785 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204500976 ecr 2204487478], length 0
 00:00:27.146311 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204514286 ecr 2204487478], length 0
 00:00:53.770236 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204540910 ecr 2204487478], length 0
 # TCP_USER_TIMEOUT = 60秒にしていた場合、以下のタイミングでタイムアウトになる
 00:01:47.534839 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2204594675 ecr 2204487478], length 0
 .
 .
 #  以下が15回目の再送
 00:13:48.504244 IP 127.0.0.1.59960 > 127.0.0.1.1: Flags [.], ack 1, win 1152, options [nop,nop,TS val 2205315572 ecr 2204487478], length 0
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      1152   0      127.0.0.1:1                  127.0.0.1:59960              

 # 開始から15分後にETIMEDOUT(Connection timed out)
[ ] SO_ERROR = 110
[ ] took: 951.382089 seconds

```

### `test-rst.py`

サーバはacceptして、`shutdown(socket.SHUT_WR)`するとFINがクライアントに飛ぶ。その後`close`するが、何も行われない。

サーバの`close`が終わってからクライアントはデータを送る。

クライアントは、1度目の`write`時にサーバから`RST`を受け取る。もちろんアプリケーションレベルだとそのことは知らずに普通に成功で返る。

クライアントは、2度目の`write`時に自分が`FIN`->`RST`を受け取っていることに気づき、データを送る前に[EPIPE] Broken pipeでエラーになる。

```
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  

 00:00:00.000000 IP 127.0.0.1.40482 > 127.0.0.1.1: Flags [S], seq 1820496075, win 65495, options [mss 65495,sackOK,TS val 2241891913 ecr 0,nop,wscale 7], length 0
 00:00:00.000084 IP 127.0.0.1.1 > 127.0.0.1.40482: Flags [S.], seq 2642886490, ack 1820496076, win 65483, options [mss 65495,sackOK,TS val 2241891913 ecr 2241891913,nop,wscale 7], length 0
 00:00:00.000123 IP 127.0.0.1.40482 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2241891913 ecr 2241891913], length 0
[c] client connect
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:40482              127.0.0.1:1                  
ESTAB      0      0      127.0.0.1:1                  127.0.0.1:40482              

[x] server accept
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:40482              127.0.0.1:1                  
ESTAB      0      0      127.0.0.1:1                  127.0.0.1:40482              

 00:00:02.016320 IP 127.0.0.1.1 > 127.0.0.1.40482: Flags [F.], seq 1, ack 1, win 512, options [nop,nop,TS val 2241893929 ecr 2241891913], length 0
 00:00:02.017333 IP 127.0.0.1.40482 > 127.0.0.1.1: Flags [.], ack 2, win 512, options [nop,nop,TS val 2241893930 ecr 2241893929], length 0

# shutdown(SHUT_WR)だけではFIN-WAIT-2のタイマーは起動していない。tcp_fin_timeoutによりtimerの秒数が変化することを確認ずみ。ちなみにshutdown(SHUT_RDWR)でも同様だったのでソケットをcloseしないとタイマーは起動しない模様
[x] server shutdown(SHUT_WR)
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
CLOSE-WAIT 1      0      127.0.0.1:40482              127.0.0.1:1                  
FIN-WAIT-2 0      0      127.0.0.1:1                  127.0.0.1:40482              

[x] server close socket
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
CLOSE-WAIT 1      0      127.0.0.1:40482              127.0.0.1:1                  
FIN-WAIT-2 0      0      127.0.0.1:1                  127.0.0.1:40482               timer:(timewait,58sec,0)

[x] send
 00:00:04.031169 IP 127.0.0.1.40482 > 127.0.0.1.1: Flags [P.], seq 1:12, ack 2, win 512, options [nop,nop,TS val 2241895944 ecr 2241893929], length 11
 00:00:04.031223 IP 127.0.0.1.1 > 127.0.0.1.40482: Flags [R], seq 2642886492, win 0, length 0

# RSTを受け取るとクライアント、サーバ両方とも即時にssの出力から消える
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  

# 2度目のsendで即時にエラー
[x] send
Traceback (most recent call last):
  File "test-rst.py", line 49, in <module>
    c.send(b"hello world")
BrokenPipeError: [Errno 32] Broken pipe
```

* `shutdown(SHUT_WR)` -> `close` ではなく、`close`のみした場合はどうなるか？ -> 上記と全く変わらない。
* `shutdown(SHUT_WR)` -> `close` ではなく、`shutdown(SHUT_RDWR)`のみした場合はどうなるか？ -> 上記と全く変わらない。
* `shutdown(SHUT_WR)` -> `close` ではなく、`shutdown(SHUT_WR)`のみした場合はどうなるか？ -> FINを飛ばすだけなのでwriteは全て成功する(直感通り)。
* `shutdown(SHUT_WR)` -> `close` ではなく、`shutdown(SHUT_RD)`のみした場合はどうなるか？ -> writeは全て成功する。shutdown(socket.SHUT_RD)のみだとおそらくTCPの動作には影響を与えないと思われる(自信ないがその他の章を参考)
* `except Exception as e:` にてwriteの例外を無視して処理を続行した場合どうなるか？ -> その後のwriteは同様に[EPIPE] Broken pipeにてエラー
* `except Exception as e:` にてwriteの例外を無視してreadした場合どうなるか？ -> その後のreadはEOFですぐ返る

### `test-rst2.py`

`test-rst.py`とほぼ同じであるが、サーバ側が`shutdown(socket.SHUT_WR)`する前に何回かデータを送っておくのだけが差分

`shutdown(SHUT_WR)`によりFINがとぶのは同じだが、その後`close`するとRSTが飛ぶ。おそらくこれはサーバ側が受信バッファにデータが残っている状態でソケットをcloseしているからである。

クライアントは、1度目の`write`時にデータ送信前に[EPIPE] Broken pipeでエラーになる。

```
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  

 00:00:00.000000 IP 127.0.0.1.42808 > 127.0.0.1.1: Flags [S], seq 150883136, win 65495, options [mss 65495,sackOK,TS val 2243051027 ecr 0,nop,wscale 7], length 0
 00:00:00.000062 IP 127.0.0.1.1 > 127.0.0.1.42808: Flags [S.], seq 876377858, ack 150883137, win 65483, options [mss 65495,sackOK,TS val 2243051027 ecr 2243051027,nop,wscale 7], length 0
 00:00:00.000101 IP 127.0.0.1.42808 > 127.0.0.1.1: Flags [.], ack 1, win 512, options [nop,nop,TS val 2243051027 ecr 2243051027], length 0
[c] client connect
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     1      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:1                  127.0.0.1:42808              
ESTAB      0      0      127.0.0.1:42808              127.0.0.1:1                  

[x] server accept
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
ESTAB      0      0      127.0.0.1:1                  127.0.0.1:42808              
ESTAB      0      0      127.0.0.1:42808              127.0.0.1:1                  

[x] send
[x] send
[x] send
 00:00:02.020492 IP 127.0.0.1.42808 > 127.0.0.1.1: Flags [P.], seq 1:12, ack 1, win 512, options [nop,nop,TS val 2243053048 ecr 2243051027], length 11
 00:00:02.020536 IP 127.0.0.1.1 > 127.0.0.1.42808: Flags [.], ack 12, win 512, options [nop,nop,TS val 2243053048 ecr 2243053048], length 0
 00:00:02.020603 IP 127.0.0.1.42808 > 127.0.0.1.1: Flags [P.], seq 12:23, ack 1, win 512, options [nop,nop,TS val 2243053048 ecr 2243053048], length 11
 00:00:02.020639 IP 127.0.0.1.1 > 127.0.0.1.42808: Flags [.], ack 23, win 512, options [nop,nop,TS val 2243053048 ecr 2243053048], length 0
 00:00:02.020710 IP 127.0.0.1.42808 > 127.0.0.1.1: Flags [P.], seq 23:34, ack 1, win 512, options [nop,nop,TS val 2243053048 ecr 2243053048], length 11
 00:00:02.020884 IP 127.0.0.1.1 > 127.0.0.1.42808: Flags [.], ack 34, win 512, options [nop,nop,TS val 2243053048 ecr 2243053048], length 0
 # shutdown(SHUT_WR)によるFIN
 00:00:02.021007 IP 127.0.0.1.1 > 127.0.0.1.42808: Flags [F.], seq 1, ack 34, win 512, options [nop,nop,TS val 2243053048 ecr 2243053048], length 0
 00:00:02.021395 IP 127.0.0.1.42808 > 127.0.0.1.1: Flags [.], ack 2, win 512, options [nop,nop,TS val 2243053048 ecr 2243053048], length 0
[x] server shutdown(SHUT_WR)
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  
FIN-WAIT-2 33     0      127.0.0.1:1                  127.0.0.1:42808              
CLOSE-WAIT 1      0      127.0.0.1:42808              127.0.0.1:1                  
 # closeによるRST
 00:00:03.033226 IP 127.0.0.1.1 > 127.0.0.1.42808: Flags [R.], seq 2, ack 34, win 512, options [nop,nop,TS val 2243054060 ecr 2243053048], length 0
[x] server close socket
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  

[x] send
Traceback (most recent call last):
  File "test-rst2.py", line 49, in <module>
    c.send(b"hello world")
BrokenPipeError: [Errno 32] Broken pipe

```

* `shutdown(SHUT_WR)` -> `close` ではなく、`close`のみした場合はどうなるか？ -> `close`時にFINをとばさずにRSTのみとばす。クライアントからみるとFIN->RSTではなく、RSTのみうけとるため、[ECONNRESET]Connection reset by peerでエラーになる。
* `shutdown(SHUT_WR)` -> `close` ではなく、`shutdown(SHUT_RDWR)`のみした場合はどうなるか？ -> `test-rst.py`のときと同じ挙動(2回目のwriteでBroken pipe)
* `shutdown(SHUT_WR)` -> `close` ではなく、`shutdown(SHUT_WR)`のみした場合はどうなるか？ -> `test-rst.py`のときと同じ挙動(正常終了)
* `shutdown(SHUT_WR)` -> `close` ではなく、`shutdown(SHUT_RD)`のみした場合はどうなるか？ -> `test-rst.py`のときと同じ挙動(正常終了)
* `close`のみした場合において、`except Exception as e:` にてwriteの例外を無視して処理を続行した場合どうなるか？ -> その後のwriteは[EPIPE] Broken pipeにてエラーに変化する!
* `except Exception as e:` にてwriteの例外を無視してreadした場合どうなるか？ -> その後のreadはEOFですぐ返る

```
[x] send
 00:00:02.011883 IP 127.0.0.1.1 > 127.0.0.1.43804: Flags [.], ack 23, win 512, options [nop,nop,TS val 2243550578 ecr 2243550578], length 0
 00:00:02.011990 IP 127.0.0.1.43804 > 127.0.0.1.1: Flags [P.], seq 23:34, ack 1, win 512, options [nop,nop,TS val 2243550579 ecr 2243550578], length 11
 00:00:02.012017 IP 127.0.0.1.1 > 127.0.0.1.43804: Flags [.], ack 34, win 512, options [nop,nop,TS val 2243550579 ecr 2243550579], length 0
 00:00:02.012073 IP 127.0.0.1.1 > 127.0.0.1.43804: Flags [R.], seq 1, ack 34, win 512, options [nop,nop,TS val 2243550579 ecr 2243550579], length 0
[x] server close socket
State      Recv-Q Send-Q Local Address:Port               Peer Address:Port              
LISTEN     0      16     127.0.0.1:1                        *:*                  

[x] send
Traceback (most recent call last):
  File "test-rst2.py", line 44, in <module>
    c.send(b"hello world")
ConnectionResetError: [Errno 104] Connection reset by peer

```

### その他
* 自分がcloseしたソケットにread/writeすると[EBADF] Bad file descriptorが返る。
* 自分がshutdown(socket.SHUT_WR)したソケットにwriteすると、[EPIPE] Broken pipeが返る。
* 自分がshutdown(socket.SHUT_RD)したソケットからreadすると、とくにエラーなく読める。が、受信バッファにデータがない場合、新たにデータを受信するかFINが送られるまでreadはブロックするのが通常だが、EOFで返却された。バッファにデータがある場合は普通に読める。
* shutdown(socket.shut_RD)したソケットに相手がデータ転送してもACKを返却する。window sizeを0にて返却してデータ転送されないようにするといった制御も行われない。
* 相手が

