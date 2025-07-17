
dev::
	npx vite

clean::
	@find .	-name \*~ -o -name .\*~ | xargs rm -fr

realclean:: clean
	@find .	-name __pycache__ -o -name .venv -o \
		-name \#\*\# -o -name .\#\* | xargs rm -fr
	@rm -fr uv.lock node_modules dist build
	@tree -I .git -a
