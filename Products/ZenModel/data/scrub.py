import re

subs = (
("\S+\@\S+\.(com|org|net)", "email@email.com"),
("\d+\.\d+\.\d+\.\d+", "1.1.1.1"),
)

lines = open("events.xml").readlines()
out = open("events.xml.new", "w")
for line in lines:
    for regex, sub in subs:
        line = re.sub(regex, sub, line) 
