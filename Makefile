TARGETS=fg bg

.PHONY: ${TARGETS}

all:
	@echo targets: ${TARGETS}

bg:
	make -C m4

chat:
	make -C m4 chat
