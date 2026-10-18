import os

with open('hd/code/makon_data.i', 'r', encoding='utf-8') as f:
    sprite_data = f.read()

parts = sprite_data.split('; Makon Sprite 1 (Right 16x32)')
spr0_data = parts[0].replace('; Makon Sprite 0 (Left 16x32)', '').strip()
spr1_data = parts[1].strip()

asm_template = """* ==========================================================
* Proyecto : Amiga 500 ASM - Sprite 32x32 Rebotando
* Fichero  : sprite_makon.s
*
* Caracteristicas:
*   - Sprite 32x32 pixeles (combinando Sprite 0 y Sprite 1)
*   - Paleta de 4 colores (Transparente + 3 colores)
*   - Movimiento suave a 50 FPS sincronizado con VBlank
*   - Rebote contra los 4 bordes de la pantalla
*   - Salida limpia al pulsar Boton Izquierdo del Raton (LMB)
* ==========================================================

; Constantes de limites de pantalla (hardware PAL/OCS)
MIN_X		EQU	130		; Borde izquierdo visible
MAX_X		EQU	416		; Borde derecho visible (448 - 32)
MIN_Y		EQU	44		; Borde superior visible
MAX_Y		EQU	266		; Borde inferior visible (298 - 32)
SPRITE_H	EQU	32		; Altura en lineas

; Offsets de Exec y Graphics Library
ExecBase	EQU	4
_LVOOpenLibrary	EQU	-408
_LVOCloseLibrary EQU	-414
_LVOLoadView	EQU	-222
_LVOWaitTOF	EQU	-270
_LVOWaitBlit	EQU	-228

; Registros Custom del Chipset Amiga
DMACONR		EQU	$dff002
VPOSR		EQU	$dff004
COP1LCH		EQU	$dff080
COPJMP1		EQU	$dff088
DMACON		EQU	$dff096
CIAA_PRA	EQU	$bfe001

		SECTION	MakonChip,CODE_C

Start:
		; Guardar todos los registros
		movem.l	d0-d7/a0-a6,-(sp)

		; Reinicializar variables por si se ejecuta varias veces (con comando 'j')
		move.w	#200,PosX
		move.w	#100,PosY
		move.w	#2,VelX
		move.w	#2,VelY

		; --------------------------------------------------
		; 1. Tomar control del sistema limpiamente
		; --------------------------------------------------
		move.l	ExecBase.w,a6
		lea	GfxName(pc),a1
		moveq	#0,d0
		jsr	_LVOOpenLibrary(a6)
		tst.l	d0
		beq	ExitDirect
		move.l	d0,GfxBase
		move.l	d0,a6			; a6 = GfxBase

		; Guardar View original y Copper original de Workbench
		move.l	$22(a6),OldView		; gb_ActiView (offset 34)
		move.l	$26(a6),OldCop		; gb_copinit (offset 38)

		; Esperar a que el sistema termine de dibujar
		jsr	_LVOWaitTOF(a6)
		suba.l	a1,a1
		jsr	_LVOLoadView(a6)	; Limpiar View
		jsr	_LVOWaitTOF(a6)
		jsr	_LVOWaitBlit(a6)	; Esperar Blitter

		; Guardar estado previo de DMA
		move.w	DMACONR,OldDma

		; --------------------------------------------------
		; 2. Configurar la Copper list y activar Sprites
		; --------------------------------------------------
		bsr	InitCopperPointers

		; Actualizar posicion inicial de ambos sprites
		bsr	UpdateSprites

		; Activar nuestra Copper list
		move.l	#CopperList,COP1LCH
		clr.w	COPJMP1

		; Desactivar bitplanes y activar DMA de Copper + Sprites
		; $82a0 = DMAF_SETCLR | DMAF_DMAEN | DMAF_COPPER | DMAF_SPREN
		move.w	#$0100,DMACON		; Desactivar bitplanes
		move.w	#$82a0,DMACON		; Activar Copper y Sprites

; ==========================================================
; Bucle Principal
; ==========================================================
MainLoop:
		; Sincronizar a 50 cuadros por segundo (VBlank)
		bsr	WaitVBL

		; Mover el Makon y rebotar si toca las paredes
		bsr	MoveSprite

		; Actualizar las palabras de control de Sprite 0 y Sprite 1
		bsr	UpdateSprites

		; Comprobar si se ha pulsado el boton izquierdo del raton (LMB)
		; CIA-A bit 6 = 0 cuando se pulsa
		btst	#6,CIAA_PRA
		bne.s	MainLoop

; ==========================================================
; Salida y Restauracion Limpia del Sistema
; ==========================================================
ExitProgram:
		; Esperar VBlank para no cortar el escaneo bruscamente
		bsr	WaitVBL

		; Apagar DMAs y restaurar estado anterior
		move.w	#$7fff,DMACON		; Desactivar todos los DMAs
		move.w	OldDma(pc),d0
		ori.w	#$8000,d0		; Activar bit SET/CLR
		move.w	d0,DMACON		; Restaurar DMAs originales

		; Restaurar Copper list original del sistema
		move.l	OldCop(pc),COP1LCH
		clr.w	COPJMP1

		; Restaurar View original de Workbench / ASM-One
		move.l	GfxBase(pc),a6
		move.l	OldView(pc),a1
		jsr	_LVOLoadView(a6)
		jsr	_LVOWaitTOF(a6)

		; Cerrar graphics.library
		move.l	ExecBase.w,a6
		move.l	GfxBase(pc),a1
		jsr	_LVOCloseLibrary(a6)

ExitDirect:
		; Restaurar registros y regresar a ASM-One
		movem.l	(sp)+,d0-d7/a0-a6
		rts

; ==========================================================
; Subrutinas
; ==========================================================

; ----------------------------------------------------------
; Espera al refresco vertical (Linea 250)
; ----------------------------------------------------------
WaitVBL:
.vbl1:
		move.l	VPOSR,d0
		andi.l	#$1ff00,d0
		cmpi.l	#$0fa00,d0
		bne.s	.vbl1
.vbl2:
		move.l	VPOSR,d0
		andi.l	#$1ff00,d0
		cmpi.l	#$0fa00,d0
		beq.s	.vbl2
		rts

; ----------------------------------------------------------
; Movimiento y Deteccion de Rebote
; ----------------------------------------------------------
MoveSprite:
		; --- Eje X ---
		move.w	PosX(pc),d0
		add.w	VelX(pc),d0

		cmpi.w	#MIN_X,d0
		bgt.s	.chkMaxX
		move.w	#MIN_X,d0
		neg.w	VelX			; Invertir direccion horizontal
		bra.s	.doneX
.chkMaxX:
		cmpi.w	#MAX_X,d0
		blt.s	.doneX
		move.w	#MAX_X,d0
		neg.w	VelX			; Invertir direccion horizontal
.doneX:
		move.w	d0,PosX

		; --- Eje Y ---
		move.w	PosY(pc),d1
		add.w	VelY(pc),d1

		cmpi.w	#MIN_Y,d1
		bgt.s	.chkMaxY
		move.w	#MIN_Y,d1
		neg.w	VelY			; Invertir direccion vertical
		bra.s	.doneY
.chkMaxY:
		cmpi.w	#MAX_Y,d1
		blt.s	.doneY
		move.w	#MAX_Y,d1
		neg.w	VelY			; Invertir direccion vertical
.doneY:
		move.w	d1,PosY
		rts

; ----------------------------------------------------------
; Actualiza Sprite 0 y Sprite 1 para formar el Makon de 32x32
; ----------------------------------------------------------
UpdateSprites:
		; Sprite 0: Mitad izquierda (16x32) en (PosX, PosY)
		lea	Makon_Spr0,a0
		move.w	PosX(pc),d0
		move.w	PosY(pc),d1
		moveq	#SPRITE_H,d2
		bsr	SetSpritePos

		; Sprite 1: Mitad derecha (16x32) en (PosX + 16, PosY)
		lea	Makon_Spr1,a0
		move.w	PosX(pc),d0
		add.w	#16,d0			; Desplazado 16 pixeles
		move.w	PosY(pc),d1
		moveq	#SPRITE_H,d2
		bsr	SetSpritePos
		rts

; ----------------------------------------------------------
; SetSpritePos
; Parametros:
;   d0.w = X (coordenada hardware)
;   d1.w = Y (coordenada hardware)
;   d2.w = Altura del sprite (32)
;   a0   = Puntero a la estructura del sprite
; ----------------------------------------------------------
SetSpritePos:
		movem.l	d0-d4,-(sp)

		; d3 = VSTOP (Y + Altura)
		move.w	d1,d3
		add.w	d2,d3

		; Word 0 (POS):
		; Byte alto = Y & $ff
		; Byte bajo = (X >> 1) & $ff
		move.w	d1,d4
		andi.w	#$00ff,d4
		lsl.w	#8,d4

		move.w	d0,-(sp)
		lsr.w	#1,d0
		andi.w	#$00ff,d0
		or.w	d0,d4
		move.w	(sp)+,d0
		move.w	d4,(a0)			; Escribir Word 0 (POS)

		; Word 1 (CTL):
		; Byte alto = VSTOP & $ff
		; Byte bajo:
		;   Bit 2 = bit 8 de Y
		;   Bit 1 = bit 8 de VSTOP
		;   Bit 0 = bit 0 de X
		;   Bit 7 = ATTACH (0)
		move.w	d3,d4
		andi.w	#$00ff,d4
		lsl.w	#8,d4

		btst	#8,d1
		beq.s	.noY8
		bset	#2,d4
.noY8:
		btst	#8,d3
		beq.s	.noVstop8
		bset	#1,d4
.noVstop8:
		btst	#0,d0
		beq.s	.noX0
		bset	#0,d4
.noX0:
		move.w	d4,2(a0)		; Escribir Word 1 (CTL)

		movem.l	(sp)+,d0-d4
		rts

; ----------------------------------------------------------
; Inicializa los punteros de sprite en la Copper list
; ----------------------------------------------------------
InitCopperPointers:
		; Sprite 0
		move.l	#Makon_Spr0,d0
		move.w	d0,CopSpr0L
		swap	d0
		move.w	d0,CopSpr0H

		; Sprite 1
		move.l	#Makon_Spr1,d0
		move.w	d0,CopSpr1L
		swap	d0
		move.w	d0,CopSpr1H

		; Sprites 2 a 7 (apuntan a NullSprite)
		move.l	#NullSprite,d0
		lea	CopSpr2H,a0
		moveq	#5,d1
.loopNull:
		swap	d0
		move.w	d0,(a0)			; CopSprXH
		swap	d0
		move.w	d0,4(a0)		; CopSprXL
		addq.w	#8,a0
		dbf	d1,.loopNull
		rts

; ==========================================================
; Datos en Chip RAM
; ==========================================================

; Variables
PosX:		dc.w	200
PosY:		dc.w	100
VelX:		dc.w	2
VelY:		dc.w	2

OldView:	dc.l	0
OldCop:		dc.l	0
OldDma:		dc.w	0
GfxBase:	dc.l	0
GfxName:	dc.b	"graphics.library",0
		EVEN

; Copper List
CopperList:
		dc.w	$0100,$0200		; BPLCON0 = 0 bitplanes (pantalla limpia)

		; Punteros Sprite 0
		dc.w	$0120
CopSpr0H:	dc.w	0
		dc.w	$0122
CopSpr0L:	dc.w	0

		; Punteros Sprite 1
		dc.w	$0124
CopSpr1H:	dc.w	0
		dc.w	$0126
CopSpr1L:	dc.w	0

		; Punteros Sprites 2 a 7
		dc.w	$0128
CopSpr2H:	dc.w	0
		dc.w	$012a
CopSpr2L:	dc.w	0

		dc.w	$012c
CopSpr3H:	dc.w	0
		dc.w	$012e
CopSpr3L:	dc.w	0

		dc.w	$0130
CopSpr4H:	dc.w	0
		dc.w	$0132
CopSpr4L:	dc.w	0

		dc.w	$0134
CopSpr5H:	dc.w	0
		dc.w	$0136
CopSpr5L:	dc.w	0

		dc.w	$0138
CopSpr6H:	dc.w	0
		dc.w	$013a
CopSpr6L:	dc.w	0

		dc.w	$013c
CopSpr7H:	dc.w	0
		dc.w	$013e
CopSpr7L:	dc.w	0

		; Paleta de Colores
		dc.w	$0180,$0124		; COLOR00: Azul pizarra oscuro de fondo
		dc.w	$01a2,$0000		; COLOR17: Negro (contorno, ojos, pies)
		dc.w	$01a4,$0889		; COLOR18: Gris medio (cuerpo peludo Makon)
		dc.w	$01a6,$0fff		; COLOR19: Blanco brillante (brillos, ojos)

		dc.w	$ffff,$fffe		; Fin de la Copper List

; Sprite vacio para desactivar sprites 2 a 7
NullSprite:
		dc.w	0,0,0,0

; ----------------------------------------------------------
; Estructura Sprite 0 (Mitad Izquierda: 16x32)
; ----------------------------------------------------------
Makon_Spr0:
		dc.w	0,0			; POS y CTL (calculadas en ejecucion)
""" + spr0_data + """
		dc.w	0,0			; Terminador de sprite

; ----------------------------------------------------------
; Estructura Sprite 1 (Mitad Derecha: 16x32)
; ----------------------------------------------------------
Makon_Spr1:
		dc.w	0,0			; POS y CTL (calculadas en ejecucion)
""" + spr1_data + """
		dc.w	0,0			; Terminador de sprite

		END
"""

with open('hd/code/sprite_makon.s', 'w', encoding='latin1') as f:
    f.write(asm_template)

print('Generated hd/code/sprite_makon.s successfully! Size:', len(asm_template), 'bytes')
