


all:
	# remove .ok if older than 15 days
	find . -name FANTOIR.zip.ok -mtime +30 -exec rm {} \;
	make FANTOIR.zip.ok

FANTOIR.zip.ok:
	wget "http://data.cquest.org/dgfip_fantoir/last.zip" -O FANTOIR.zip.tmp
	# remove file smaller thant 50M
	find . -name FANTOIR.zip.tmp -size -50M -exec rm {} \;
	mv -f FANTOIR.zip.tmp FANTOIR.zip
	touch FANTOIR.zip.ok

clean distclean:
	rm -f *.zip.ok
	rm -f *.zip.tmp
	rm -f *.zip

