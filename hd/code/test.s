; ==========================================================
; Proyecto : Prueba ASM Amiga 500
; Fichero  : test.s
; Descripción:
;   "Hello World" visual para Amiga 500.
;   Muestra barras de color (efecto raster) en el fondo
;   modificando COLOR00 con la posición del rayo ($dff006).
;
;   Para salir: Pulsa el BOTÓN IZQUIERDO del ratón.
; ==========================================================

		SECTION	Code,CODE

Start:
		; Guardar registros por seguridad y buena práctica
		movem.l	d0-d7/a0-a6,-(sp)

.MainLoop:
		; 1. Efecto visual:
		; Leemos el registro VHPOSR ($dff006) que contiene la
		; posición vertical y horizontal actual del rayo de la pantalla,
		; y lo enviamos al registro COLOR00 ($dff180).
		; Esto genera barras de colores continuas estilo "copper/raster".
		move.w	$dff006,$dff180

		; 2. Comprobar el botón izquierdo del ratón (LMB):
		; El registro de la CIA-A ($bfe001), bit 6, indica el estado del botón.
		; Si el bit 6 es 0 -> botón presionado.
		; Si el bit 6 es 1 -> botón sin presionar.
		btst	#6,$bfe001
		bne.s	.MainLoop		; Si no se pulsa, seguimos en bucle

		; 3. Restaurar el color negro de fondo ($000)
		move.w	#$000,$dff180

		; 4. Restaurar registros y regresar limpiamente a ASM-One
		movem.l	(sp)+,d0-d7/a0-a6
		rts
