bits 16
org 0x8000

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    sti
    mov ax, 0x0003
    int 0x10

    mov si, welcome_message
    call print_string
    mov si, help_hint
    call print_string

command_loop:
    mov si, prompt
    call print_string
    mov word [input_length], 0

.read_key:
    xor ah, ah
    int 0x16
    cmp al, 13
    je .submit
    cmp al, 8
    je .backspace
    cmp al, 32
    jb .read_key
    cmp word [input_length], 63
    jae .read_key

    cmp al, 'a'
    jb .store
    cmp al, 'z'
    ja .store
    sub al, 32
.store:
    mov bx, [input_length]
    mov [input_buffer + bx], al
    inc word [input_length]
    call print_char
    jmp .read_key

.backspace:
    cmp word [input_length], 0
    je .read_key
    dec word [input_length]
    mov bx, [input_length]
    mov byte [input_buffer + bx], 0
    mov al, 8
    call print_char
    mov al, ' '
    call print_char
    mov al, 8
    call print_char
    jmp .read_key

.submit:
    mov bx, [input_length]
    mov byte [input_buffer + bx], 0
    call print_newline

    mov si, input_buffer
    mov di, command_help
    call compare_string
    jnc .help

    mov si, input_buffer
    mov di, command_ver
    call compare_string
    jnc .version

    mov si, input_buffer
    mov di, command_cls
    call compare_string
    jnc .clear

    mov si, input_buffer
    mov di, command_reboot
    call compare_string
    jnc .reboot

    mov si, input_buffer
    mov di, command_echo
    call compare_string
    jnc .echo

    cmp byte [input_buffer], 0
    je command_loop
    mov si, unknown_message
    call print_string
    jmp command_loop

.help:
    mov si, help_message
    call print_string
    jmp command_loop

.version:
    mov si, version_message
    call print_string
    jmp command_loop

.clear:
    mov ax, 0x0003
    int 0x10
    jmp command_loop

.reboot:
    mov si, reboot_message
    call print_string
    int 0x19
    jmp $

.echo:
    mov si, input_buffer + 5
    call print_string
    call print_newline
    jmp command_loop

print_string:
    lodsb
    test al, al
    jz .done
    call print_char
    jmp print_string
.done:
    ret

print_char:
    mov ah, 0x0e
    mov bh, 0
    mov bl, 0x07
    int 0x10
    ret

print_newline:
    mov al, 13
    call print_char
    mov al, 10
    call print_char
    ret

compare_string:
.next:
    lodsb
    scasb
    jne .different
    test al, al
    jnz .next
    clc
    ret
.different:
    stc
    ret

welcome_message db "JadevOS Computers [Version 1.0.0]", 13, 10, 0
help_hint db "Escribe HELP para ver los comandos.", 13, 10, 0
prompt db "C:\>", 0
help_message db "HELP VER CLS ECHO texto REBOOT", 13, 10, 0
version_message db "JadevOS Computers [Version 1.0.0]", 13, 10, 0
unknown_message db "Comando no reconocido. Escribe HELP.", 13, 10, 0
reboot_message db "Reiniciando...", 13, 10, 0
command_help db "HELP", 0
command_ver db "VER", 0
command_cls db "CLS", 0
command_reboot db "REBOOT", 0
command_echo db "ECHO ", 0
input_length dw 0
input_buffer times 64 db 0
