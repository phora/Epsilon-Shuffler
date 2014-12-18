import random
import sys
import os
import configparser
import csv
import subprocess
import atexit

EPSILON_SHUFFLER_CFG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'epsilon-shuffler')
EPSILON_SHUFFLER_CFG_INI = os.path.join(EPSILON_SHUFFLER_CFG_DIR, 'epsilon-shuffler.ini')
EPSILON_SHUFFLER_DB_STORE = os.path.join(EPSILON_SHUFFLER_CFG_DIR, 'epsilon-shuffer-scores.tsv')
music_db = {}
cfg = configparser.ConfigParser()
cfg.read(EPSILON_SHUFFLER_CFG_INI)

folders_to_shuffle = cfg.get('DEFAULT', 'paths', fallback='').split('\n')
music_exts = cfg.get('DEFAULT', 'exts', fallback='.mp3').split(',')
epsilon_value = cfg.getfloat('DEFAULT', 'epsilon_value', fallback=0.1)

#exit code for manual exit is 123
#ffplay -autoexit $ALARM_SOUND -nodisp -hide_banner

# see http://python4fun.blogspot.com/2008/06/get-key-press-in-python.html
import termios, sys, os
TERMIOS = termios

def getkey():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    new[3] = new[3] & ~TERMIOS.ICANON & ~TERMIOS.ECHO
    new[6][TERMIOS.VMIN] = 1
    new[6][TERMIOS.VTIME] = 0
    termios.tcsetattr(fd, TERMIOS.TCSANOW, new)
    c = None
    try:
        c = os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, TERMIOS.TCSAFLUSH, old)
    return c


class EpsilonItem:
	def __init__(self, score=0, trials=0):
		self.score=score
		self.trials=trials

def epsilon_select(items, eps):
	rndm = random.random()
	if rndm < eps:
		return random.choice(items)
	else:
		return max(items, key=lambda x: x[1].score/x[1].trials if x[1].trials>0 else 0)

def play(fname):
	music_proc = subprocess.Popen(['ffplay', '-autoexit', '-nodisp', '-hide_banner', fname])
	rewarded = True
	while music_proc.poll() is None:
		c = getkey().decode('utf-8')
		print(c)
		if c == '-':
			skipped = False
			music_proc.terminate()
			music_proc.wait()
			print(music_proc.returncode)
	return rewarded

def write_db():
	print("Writing DB...")
	with open(EPSILON_SHUFFLER_DB_STORE, 'w') as tsvfile:
		writer = csv.writer(tsvfile, delimiter='\t')
		for k,v in music_db.items():
			writer.writerow([k, v.score, v.trials])

if not os.path.exists(EPSILON_SHUFFLER_CFG_DIR):
	os.makedirs(EPSILON_SHUFFLER_CFG_DIR)
if os.path.exists(EPSILON_SHUFFLER_DB_STORE):
	with open(EPSILON_SHUFFLER_DB_STORE) as tsvfile:
		reader = csv.reader(tsvfile, delimiter='\t')
		for row in reader:
			music_db[row[0]]=EpsilonItem(score=row[1], trials=row[2])

for item in sys.argv[1:]:
	if item not in music_db.keys():
		music_db[item]=EpsilonItem()

atexit.register(write_db)

while True:
	item = epsilon_select(list(music_db.items()), epsilon_value)
	rewarded = play(item[0])
	if rewarded:
		print("Rewarded, increasing probability")
		item[1].score+=1
	else:
		print("Not rewarded, decreasing probability")
		item[1].score-=1
	item[1].trials+=1
