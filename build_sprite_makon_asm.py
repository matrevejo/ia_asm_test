with open('hd/code/makon_data.i', 'r', encoding='utf-8') as f:
    sprite_data = f.read()

parts = sprite_data.split('; Makon Sprite 1 (Right 16x32)')
spr0_data = parts[0].replace('; Makon Sprite 0 (Left 16x32)', '').strip()
spr1_data = parts[1].strip()

asm_content = """* ==========================================================
* Proyecto : Amiga 500 ASM - Makon 32x32 Rebotando
* Fichero  : sprite_makon.s
*
* Caracteristicas:
*   - Sprite de 32x32 pixeles (combinando Sprite 0 y Sprite 1)
*   - Ventana de visualizacion PAL completa (DIWSTRT / DIWSTOP)
*   - Acceso a registros Custom mediante base a5 ($dff000)
*   - Sincronizacion a 50 FPS con VBlank
*   - Rebote continuo contra los 4 bordes de la pantalla
*   - Salida limpia a ASM-One con el Boton Izquierdo (LMB)
* ==========================================================

; Constantes de limites de pantalla visible (hardware PAL)
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

		SECTION	MakonChip,CODE_C

Start:
		; Guardar todos los registros de la CPU
		movem.l	d0-d7/a0-a6,-(sp)

		; a5 = Puntero base permanente a los registros del Chipset ($dff000)
		lea	$dff000,a5

		; Reinicializar variables de estado
		move.w	#200,PosX
		move.w	#100,PosY
		move.w	#2,VelX
		move.w	#2,VelY

		; --------------------------------------------------
		; 1. Abrir Graphics Library y guardar estado del OS
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

		; Esperar fin de cuadro y desconectar View del OS
		jsr	_LVOWaitTOF(a6)
		suba.l	a1,a1
		jsr	_LVOLoadView(a6)	; Limpiar View
		jsr	_LVOWaitTOF(a6)
		jsr	_LVOWaitBlit(a6)	; Esperar Blitter

		; Guardar estado previo de DMA
		move.w	$002(a5),OldDma		; DMACONR

		; --------------------------------------------------
		; 2. Preparar Copper List y Activar Hardware
		; --------------------------------------------------
		; Escribir punteros de Sprite 0 y Sprite 1 en la Copper list
		bsr	InitCopperPointers

		; Calcular posicion inicial en palabras de control de los sprites
		bsr	UpdateSprites

		; Cargar nuestra Copper List en el hardware
		move.l	#CopperList,$080(a5)	; COP1LCH
		move.w	#0,$088(a5)		; COPJMP1 (estroboscopico para iniciar Copper)

		; Desactivar bitplanes y activar Copper + Sprites
		move.w	#$0100,$096(a5)		; Desactivar Bitplane DMA
		move.w	#$82a0,$096(a5)		; Activar DMAEN | COPEN | SPREN

; ==========================================================
; Bucle Principal
; ==========================================================
MainLoop:
		; Esperar al refresco vertical (50 FPS)
		bsr	WaitVBL

		; Actualizar posicion y rebotar si toca los bordes
		bsr	MoveSprite

		; Actualizar coordenadas de los sprites para el siguiente cuadro
		bsr	UpdateSprites

		; Comprobar el boton izquierdo del raton (LMB)
		; CIA-A ($bfe001) bit 6 = 0 cuando se presiona
		btst	#6,$bfe001
		bne.s	MainLoop

; ==========================================================
; Salida y Restauracion Limpia del Sistema
; ==========================================================
ExitProgram:
		bsr	WaitVBL

		; Apagar DMAs y restaurar el estado original del sistema
		move.w	#$7fff,$096(a5)		; Desactivar todos los DMAs
		move.w	OldDma(pc),d0
		ori.w	#$8000,d0		; Activar bit SET/CLR
		move.w	d0,$096(a5)		; Restaurar DMAs

		; Restaurar Copper original del sistema
		move.l	OldCop(pc),$080(a5)	; COP1LCH
		move.w	#0,$088(a5)		; COPJMP1

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
		movem.l	(sp)+,d0-d7/a0-a6
		rts

; ==========================================================
; Subrutinas
; ==========================================================

; ----------------------------------------------------------
; Espera al inicio del borrado vertical (VBlank - linea 250)
; Usa a5 ($dff000) para garantizar acceso exacto sin bugs de bus
; ----------------------------------------------------------
WaitVBL:
.wait1:
		move.l	$004(a5),d0		; Leer VPOSR / VHPOSR ($dff004)
		andi.l	#$1ff00,d0
		cmpi.l	#$0fa00,d0		; Linea 250 ($FA)
		bne.s	.wait1
.wait2:
		move.l	$004(a5),d0
		andi.l	#$1ff00,d0
		cmpi.l	#$0fa00,d0
		beq.s	.wait2
		rts

; ----------------------------------------------------------
; Movimiento con Rebote en los 4 bordes
; ----------------------------------------------------------
MoveSprite:
		; --- Eje Horizontal (X) ---
		move.w	PosX(pc),d0
		add.w	VelX(pc),d0

		cmpi.w	#MIN_X,d0
		bgt.s	.chkMaxX
		move.w	#MIN_X,d0
		move.w	VelX(pc),d2
		neg.w	d2
		move.w	d2,VelX
		bra.s	.doneX
.chkMaxX:
		cmpi.w	#MAX_X,d0
		blt.s	.doneX
		move.w	#MAX_X,d0
		move.w	VelX(pc),d2
		neg.w	d2
		move.w	d2,VelX
.doneX:
		move.w	d0,PosX

		; --- Eje Vertical (Y) ---
		move.w	PosY(pc),d1
		add.w	VelY(pc),d1

		cmpi.w	#MIN_Y,d1
		bgt.s	.chkMaxY
		move.w	#MIN_Y,d1
		move.w	VelY(pc),d2
		neg.w	d2
		move.w	d2,VelY
		bra.s	.doneY
.chkMaxY:
		cmpi.w	#MAX_Y,d1
		blt.s	.doneY
		move.w	#MAX_Y,d1
		move.w	VelY(pc),d2
		neg.w	d2
		move.w	d2,VelY
.doneY:
		move.w	d1,PosY
		rts

; ----------------------------------------------------------
; Actualiza Sprite 0 y Sprite 1
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
		add.w	#16,d0			; 16 pixeles a la derecha
		move.w	PosY(pc),d1
		moveq	#SPRITE_H,d2
		bsr	SetSpritePos
		rts

; ----------------------------------------------------------
; SetSpritePos: Empaqueta coordenadas en las cabeceras POS y CTL
; Entrada:
;   d0.w = X
;   d1.w = Y
;   d2.w = Altura (32)
;   a0   = Puntero al Sprite en Chip RAM
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
		move.w	d4,(a0)			; Escribir POS

		; Word 1 (CTL):
		; Byte alto = VSTOP & $ff
		; Byte bajo:
		;   Bit 2 = bit 8 de Y
		;   Bit 1 = bit 8 de VSTOP
		;   Bit 0 = bit 0 de X
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
		move.w	d4,2(a0)		; Escribir CTL

		movem.l	(sp)+,d0-d4
		rts

; ----------------------------------------------------------
; Escribe los punteros de Chip RAM dentro de la Copper List
; ----------------------------------------------------------
InitCopperPointers:
		lea	CopperList,a0

		; Sprite 0 (Mitad Izquierda) -> Offsets 22 (High) y 26 (Low)
		move.l	#Makon_Spr0,d0
		move.w	d0,26(a0)		; SPR0PTL
		swap	d0
		move.w	d0,22(a0)		; SPR0PTH

		; Sprite 1 (Mitad Derecha) -> Offsets 30 (High) y 34 (Low)
		move.l	#Makon_Spr1,d0
		move.w	d0,34(a0)		; SPR1PTL
		swap	d0
		move.w	d0,30(a0)		; SPR1PTH

		; Sprites 2 a 7 -> apuntar a NullSprite (desde offset 36)
		move.l	#NullSprite,d0
		lea	36(a0),a1
		moveq	#5,d1			; 6 sprites (2 a 7)
.loopNull:
		swap	d0
		move.w	d0,2(a1)		; SPRxPTH
		swap	d0
		move.w	d0,6(a1)		; SPRxPTL
		addq.w	#8,a1
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

; ----------------------------------------------------------
; Copper List (Cada instruccion ocupa exactamente 4 bytes)
; ----------------------------------------------------------
CopperList:
		; 1. Definicion de la ventana visible de visualizacion (DIW)
		dc.w	$008e,$2c81		; Offset  0: DIWSTRT (Linea $2c, Horiz $81)
		dc.w	$0090,$2cc1		; Offset  4: DIWSTOP (Linea $2c, Horiz $c1)
		dc.w	$0100,$0200		; Offset  8: BPLCON0 (0 bitplanes, COLOR burst activo)
		dc.w	$0102,$0000		; Offset 12: BPLCON1 (Scroll = 0)
		dc.w	$0104,$0024		; Offset 16: BPLCON2 (Sprites con maxima prioridad)

		; 2. Punteros de Sprites (Rellenados en ejecucion por InitCopperPointers)
		dc.w	$0120,0			; Offset 20: SPR0PTH (Sprite 0 High)
		dc.w	$0122,0			; Offset 24: SPR0PTL (Sprite 0 Low)
		dc.w	$0124,0			; Offset 28: SPR1PTH (Sprite 1 High)
		dc.w	$0126,0			; Offset 32: SPR1PTL (Sprite 1 Low)

		dc.w	$0128,0			; Offset 36: SPR2PTH
		dc.w	$012a,0			; Offset 40: SPR2PTL
		dc.w	$012c,0			; Offset 44: SPR3PTH
		dc.w	$012e,0			; Offset 48: SPR3PTL
		dc.w	$0130,0			; Offset 52: SPR4PTH
		dc.w	$0132,0			; Offset 56: SPR4PTL
		dc.w	$0134,0			; Offset 60: SPR5PTH
		dc.w	$0136,0			; Offset 64: SPR5PTL
		dc.w	$0138,0			; Offset 68: SPR6PTH
		dc.w	$013a,0			; Offset 72: SPR6PTL
		dc.w	$013c,0			; Offset 76: SPR7PTH
		dc.w	$013e,0			; Offset 80: SPR7PTL

		; 3. Paleta de Colores
		dc.w	$0180,$0124		; Offset 84: COLOR00: Fondo Azul Pizarra Oscuro
		dc.w	$01a2,$0000		; Offset 88: COLOR17: Negro (Contornos Makon)
		dc.w	$01a4,$0889		; Offset 92: COLOR18: Gris (Pelaje Makon)
		dc.w	$01a6,$0fff		; Offset 96: COLOR19: Blanco brillante (Ojos Makon)

		; Fin de la Copper List
		dc.w	$ffff,$fffe

; Sprite nulo (terminador inmediato) para apagar los canales 2 a 7
NullSprite:
		dc.w	0,0,0,0

; ----------------------------------------------------------
; Estructura Sprite 0 (Mitad Izquierda: 16x32)
; ----------------------------------------------------------
Makon_Spr0:
		dc.w	0,0			; POS y CTL (actualizados cada cuadro)
""" + spr0_data + """
		dc.w	0,0			; Terminador de sprite

; ----------------------------------------------------------
; Estructura Sprite 1 (Mitad Derecha: 16x32)
; ----------------------------------------------------------
Makon_Spr1:
		dc.w	0,0			; POS y CTL (actualizados cada cuadro)
""" + spr1_data + """
		dc.w	0,0			; Terminador de sprite

		END
"""

with open('hd/code/sprite_makon.s', 'w', encoding='latin1') as f:
    f.write(asm_content)

print('Updated hd/code/sprite_makon.s with bulletproof hardware code!')
