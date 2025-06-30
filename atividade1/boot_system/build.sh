#!/bin/bash

echo "=== Compilando Sistema de Boot ==="

# Limpar arquivos anteriores
rm -f *.bin *.o disk.img

# 1. Compilar bootloader
echo "Compilando bootloader..."
nasm -f bin bootloader.asm -o bootloader.bin
if [ $? -ne 0 ]; then
    echo "Erro ao compilar bootloader!"
    exit 1
fi

# 2. Compilar kernel
echo "Compilando kernel..."
gcc -m32 -ffreestanding -nostdlib -nostdinc -fno-pie -fno-stack-protector \
    -mno-red-zone -mno-mmx -mno-sse -mno-sse2 -fno-builtin \
    -Wall -Wno-unused-variable -O2 \
    -c kernel.c -o kernel.o

if [ $? -ne 0 ]; then
    echo "Erro ao compilar kernel!"
    exit 1
fi

# 3. Linkar kernel
echo "Linkando kernel..."
ld -m elf_i386 -Ttext 0x1000 --oformat binary kernel.o -o kernel.bin
if [ $? -ne 0 ]; then
    echo "Erro ao linkar kernel!"
    exit 1
fi

# 4. Verificar tamanhos
echo "Verificando tamanhos dos arquivos..."
bootloader_size=$(stat -c%s bootloader.bin)
kernel_size=$(stat -c%s kernel.bin)

echo "Bootloader: $bootloader_size bytes"
echo "Kernel: $kernel_size bytes"

if [ $bootloader_size -gt 512 ]; then
    echo "ERRO: Bootloader muito grande! (máximo 512 bytes)"
    exit 1
fi

# 5. Criar imagem de disco (1.44MB floppy)
echo "Criando imagem de disco..."
dd if=/dev/zero of=disk.img bs=512 count=2880 2>/dev/null

# 6. Copiar bootloader para o primeiro setor
dd if=bootloader.bin of=disk.img bs=512 count=1 conv=notrunc 2>/dev/null

# 7. Copiar kernel a partir do segundo setor
dd if=kernel.bin of=disk.img bs=512 seek=1 conv=notrunc 2>/dev/null

echo ""
echo "=== Compilação Concluída! ==="
echo "Arquivo criado: disk.img"
echo ""
echo "Para testar:"
echo "  qemu-system-i386 -fda disk.img"
echo ""
echo "Para usar no VirtualBox:"
echo "  1. Criar nova VM (tipo: Other/DOS)"
echo "  2. Configurar floppy disk apontando para disk.img"
echo "  3. Iniciar VM"