* ==========================================================
* Proyecto : Amiga 500 ASM - Makon Estatico en el Centro
* Fichero  : sprite_static.s
*
* Muestra el Makon de 32x32 estatico en el centro de la pantalla
* (X = 272, Y = 156) sobre fondo azul pizarra.
*
* Pulsa el BOTON IZQUIERDO del raton (LMB) para salir.
* ==========================================================

; Offsets de Exec y Graphics Library
ExecBase	EQU	4
_LVOForbid	EQU	-132
_LVOPermit	EQU	-138
_LVOOpenLibrary	EQU	-408
_LVOCloseLibrary EQU	-414

		SECTION	MakonChip,CODE_C

Start:
		; Guardar todos los registros de la CPU
		movem.l	d0-d7/a0-a6,-(sp)
		lea	$dff000,a5		; a5 = base Custom Chips $dff000

		; 1. Desactivar multitarea del OS
		move.l	ExecBase.w,a6
		jsr	_LVOForbid(a6)

		; 2. Abrir Graphics Library para guardar el Copper original de Workbench
		lea	GfxName(pc),a1
		moveq	#0,d0
		jsr	_LVOOpenLibrary(a6)
		move.l	d0,GfxBase
		move.l	d0,a4
		move.l	$26(a4),OldCop		; Guardar GfxBase->copinit (offset 38 = $26)

		; 3. Guardar estado de interrupciones y DMA del sistema
		move.w	$01c(a5),d0		; INTENAR
		ori.w	#$8000,d0
		move.w	d0,OldInt

		move.w	$002(a5),d0		; DMACONR
		ori.w	#$8000,d0
		move.w	d0,OldDma

		; 4. Desactivar interrupciones para que el OS no interfiera
		move.w	#$7fff,$09a(a5)		; INTENA disable all
		move.w	#$7fff,$09c(a5)		; INTREQ clear all

		; Desactivar todos los canales DMA actuales
		move.w	#$7fff,$096(a5)		; DMACON disable all

		; 5. Inicializar punteros de la Copper list
		bsr	InitCopperPointers

		; 6. Instalar y activar nuestra Copper list
		move.l	#CopperList,$080(a5)	; COP1LCH
		move.w	#0,$088(a5)		; COPJMP1

		; Activar DMA de Copper y Sprites
		; $82a0 = DMAF_SETCLR | DMAF_DMAEN | DMAF_COPPER | DMAF_SPREN
		move.w	#$82a0,$096(a5)

; ==========================================================
; Bucle: El Makon se muestra estatico en el centro
; Pulsa el Boton Izquierdo del Raton (LMB) para salir
; ==========================================================
MainLoop:
		btst	#6,$bfe001		; ¿Boton izquierdo pulsado? (0 = si)
		bne.s	MainLoop

; ==========================================================
; Salida y Restauracion Limpia del Sistema
; ==========================================================
ExitProgram:
		; Apagar nuestros DMAs
		move.w	#$7fff,$096(a5)

		; Restaurar Copper del sistema
		move.l	OldCop(pc),$080(a5)
		move.w	#0,$088(a5)

		; Restaurar DMAs originales del sistema
		move.w	OldDma(pc),d0
		move.w	d0,$096(a5)

		; Restaurar Interrupciones originales
		move.w	OldInt(pc),d0
		move.w	d0,$09a(a5)

		; Cerrar graphics.library
		move.l	ExecBase.w,a6
		move.l	GfxBase(pc),a1
		jsr	_LVOCloseLibrary(a6)

		; Re-activar multitarea del OS
		jsr	_LVOPermit(a6)

		; Restaurar registros de la CPU y salir a ASM-One
		movem.l	(sp)+,d0-d7/a0-a6
		rts

; ==========================================================
; Subrutina: Inicializar punteros de Sprites en CopperList
; ==========================================================
InitCopperPointers:
		; Sprite 0 -> Makon_Spr0 (Mitad Izquierda)
		move.l	#Makon_Spr0,d0
		move.w	d0,CopSpr0L
		swap	d0
		move.w	d0,CopSpr0H

		; Sprite 1 -> Makon_Spr1 (Mitad Derecha)
		move.l	#Makon_Spr1,d0
		move.w	d0,CopSpr1L
		swap	d0
		move.w	d0,CopSpr1H

		; Sprites 2 a 7 -> NullSprite (apagados)
		move.l	#NullSprite,d0
		move.w	d0,CopSpr2L
		move.w	d0,CopSpr3L
		move.w	d0,CopSpr4L
		move.w	d0,CopSpr5L
		move.w	d0,CopSpr6L
		move.w	d0,CopSpr7L
		swap	d0
		move.w	d0,CopSpr2H
		move.w	d0,CopSpr3H
		move.w	d0,CopSpr4H
		move.w	d0,CopSpr5H
		move.w	d0,CopSpr6H
		move.w	d0,CopSpr7H
		rts

; ==========================================================
; Datos en Chip RAM
; ==========================================================

OldCop:		dc.l	0
OldInt:		dc.w	0
OldDma:		dc.w	0
GfxBase:	dc.l	0
GfxName:	dc.b	"graphics.library",0
		EVEN

; ----------------------------------------------------------
; Copper List
; ----------------------------------------------------------
CopperList:
		; 1. Apertura de la ventana visible PAL (DIW)
		dc.w	$008e,$2c81		; DIWSTRT (Linea $2c, Horiz $81)
		dc.w	$0090,$2cc1		; DIWSTOP (Linea $2c, Horiz $c1)
		dc.w	$0100,$0200		; BPLCON0 = 0 bitplanes, COLOR activo
		dc.w	$0102,$0000		; BPLCON1 = 0
		dc.w	$0104,$0024		; BPLCON2 = Sprites prioridad alta

		; 2. Punteros a los 8 sprites hardware
		dc.w	$0120
CopSpr0H:	dc.w	0
		dc.w	$0122
CopSpr0L:	dc.w	0

		dc.w	$0124
CopSpr1H:	dc.w	0
		dc.w	$0126
CopSpr1L:	dc.w	0

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

		; 3. Paleta de Colores
		dc.w	$0180,$0124		; COLOR00: Fondo Azul Pizarra
		dc.w	$01a2,$0000		; COLOR17: Negro (Contornos Makon)
		dc.w	$01a4,$0889		; COLOR18: Gris (Pelaje Makon)
		dc.w	$01a6,$0fff		; COLOR19: Blanco (Ojos/Brillos Makon)

		; Fin de la Copper list
		dc.w	$ffff,$fffe

; Sprite nulo para canales 2 a 7
NullSprite:
		dc.w	0,0,0,0

; ----------------------------------------------------------
; Estructura Sprite 0 (Mitad Izquierda: 16x32)
; Pre-posicionado en X = 272, Y = 156
; Word 0 (POS) = $9C88 (Y=$9C, X>>1=136=$88)
; Word 1 (CTL) = $BC00 (VSTOP=156+32=188=$BC)
; ----------------------------------------------------------
Makon_Spr0:
		dc.w	$9c88,$bc00
		dc.w	$0024,$0002	; Line 00
		dc.w	$0024,$001b	; Line 01
		dc.w	$008c,$007f	; Line 02
		dc.w	$0098,$007f	; Line 03
		dc.w	$0120,$00ff	; Line 04
		dc.w	$0352,$00ed	; Line 05
		dc.w	$0174,$00cf	; Line 06
		dc.w	$0148,$00ff	; Line 07
		dc.w	$002c,$01ff	; Line 08
		dc.w	$0361,$00ff	; Line 09
		dc.w	$01f7,$00fb	; Line 10
		dc.w	$00b3,$01ff	; Line 11
		dc.w	$0067,$01ff	; Line 12
		dc.w	$0367,$00ff	; Line 13
		dc.w	$03ff,$00f3	; Line 14
		dc.w	$0276,$01f9	; Line 15
		dc.w	$034d,$00fe	; Line 16
		dc.w	$035e,$00ff	; Line 17
		dc.w	$0173,$00ff	; Line 18
		dc.w	$0377,$00ff	; Line 19
		dc.w	$0327,$00ff	; Line 20
		dc.w	$0147,$00bf	; Line 21
		dc.w	$0102,$00ff	; Line 22
		dc.w	$0100,$00ff	; Line 23
		dc.w	$0180,$007f	; Line 24
		dc.w	$00f8,$0007	; Line 25
		dc.w	$00ff,$0000	; Line 26
		dc.w	$000a,$0004	; Line 27
		dc.w	$0006,$000c	; Line 28
		dc.w	$002c,$001e	; Line 29
		dc.w	$004a,$003c	; Line 30
		dc.w	$007c,$0000	; Line 31
		dc.w	0,0			; Terminador de sprite

; ----------------------------------------------------------
; Estructura Sprite 1 (Mitad Derecha: 16x32)
; Pre-posicionado en X = 288, Y = 156 (X_Spr0 + 16)
; Word 0 (POS) = $9C90 (Y=$9C, X>>1=144=$90)
; Word 1 (CTL) = $BC00 (VSTOP=156+32=188=$BC)
; ----------------------------------------------------------
Makon_Spr1:
		dc.w	$9c90,$bc00
		dc.w	$2000,$0000	; Line 00
		dc.w	$bc00,$4000	; Line 01
		dc.w	$4080,$ff00	; Line 02
		dc.w	$7dc0,$fe00	; Line 03
		dc.w	$8080,$ff00	; Line 04
		dc.w	$42c0,$bf00	; Line 05
		dc.w	$3fc0,$f300	; Line 06
		dc.w	$1000,$ff80	; Line 07
		dc.w	$b640,$ff80	; Line 08
		dc.w	$87c0,$ff00	; Line 09
		dc.w	$ef00,$df80	; Line 10
		dc.w	$cd40,$ff80	; Line 11
		dc.w	$f540,$ff80	; Line 12
		dc.w	$e740,$ff80	; Line 13
		dc.w	$d740,$ef80	; Line 14
		dc.w	$2b40,$df80	; Line 15
		dc.w	$d540,$3f80	; Line 16
		dc.w	$7e40,$ff80	; Line 17
		dc.w	$f640,$ff80	; Line 18
		dc.w	$b4c0,$ff00	; Line 19
		dc.w	$9cc0,$ff00	; Line 20
		dc.w	$b8c0,$ff00	; Line 21
		dc.w	$34c0,$fb00	; Line 22
		dc.w	$0080,$ff00	; Line 23
		dc.w	$0080,$ff00	; Line 24
		dc.w	$6f80,$9000	; Line 25
		dc.w	$ff80,$0000	; Line 26
		dc.w	$5000,$2000	; Line 27
		dc.w	$4000,$3000	; Line 28
		dc.w	$7400,$3800	; Line 29
		dc.w	$5300,$3c00	; Line 30
		dc.w	$1600,$0800	; Line 31
		dc.w	0,0			; Terminador de sprite

		END
