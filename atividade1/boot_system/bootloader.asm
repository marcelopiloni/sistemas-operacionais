[org 0x7c00]        ; Bootloader carrega em 0x7c00
[bits 16]           ; Modo real 16 bits

start:
    ; Configurar segmentos
    mov ax, 0
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7c00

    ; Limpar tela
    mov ah, 0x00
    mov al, 0x03
    int 0x10

    ; Mostrar mensagem de boot
    mov si, boot_msg
    call print_string

    ; Carregar kernel do disco
    mov ah, 0x02        ; Função de leitura
    mov al, 1           ; 1 setor
    mov ch, 0           ; Cilindro 0
    mov cl, 2           ; Setor 2
    mov dh, 0           ; Cabeça 0
    mov dl, 0x80        ; Drive 0
    mov bx, 0x1000      ; Carregar em 0x1000
    int 0x13            ; Interrupção BIOS

    ; Pular para o kernel
    jmp 0x1000

print_string:
    mov ah, 0x0e
.loop:
    lodsb
    cmp al, 0
    je .done
    int 0x10
    jmp .loop
.done:
    ret

boot_msg db 'Bootloader iniciado! Carregando sistema...', 13, 10, 0

; Preencher até 510 bytes
times 510-($-$$) db 0
dw 0xaa55           ; Assinatura de boot