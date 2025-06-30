// kernel.c - Versão final sem assembly inline

// Definições de tipos básicos
typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;

// Definições básicas
#define VIDEO_MEMORY 0xb8000
#define SCREEN_WIDTH 80
#define SCREEN_HEIGHT 25

// Estruturas de dados
struct Pessoa {
    char nome[30];
    int idade;
    char cpf[12];
    int ativo;
};

struct Produto {
    char nome[30];
    int preco;
    int quantidade;
    int ativo;
};

// Variáveis globais
static struct Pessoa pessoas[50];
static struct Produto produtos[50];
static int num_pessoas = 0;
static int num_produtos = 0;
static int cursor_x = 0, cursor_y = 0;
// Removido input_counter não usado

// Funções básicas de I/O
void putchar(char c) {
    uint16_t *video = (uint16_t*)VIDEO_MEMORY;
    
    if (c == '\n') {
        cursor_x = 0;
        cursor_y++;
    } else if (c == '\r') {
        cursor_x = 0;
    } else if (c == '\b') {
        if (cursor_x > 0) {
            cursor_x--;
            video[cursor_y * SCREEN_WIDTH + cursor_x] = (0x0F << 8) | ' ';
        }
    } else {
        video[cursor_y * SCREEN_WIDTH + cursor_x] = (0x0F << 8) | c;
        cursor_x++;
    }
    
    if (cursor_x >= SCREEN_WIDTH) {
        cursor_x = 0;
        cursor_y++;
    }
    
    if (cursor_y >= SCREEN_HEIGHT) {
        // Scroll simples - limpar tela
        for (int i = 0; i < SCREEN_WIDTH * SCREEN_HEIGHT; i++) {
            video[i] = (0x0F << 8) | ' ';
        }
        cursor_x = 0;
        cursor_y = 0;
    }
}

void print(const char* str) {
    while (*str) {
        putchar(*str);
        str++;
    }
}

void print_int(int num) {
    if (num == 0) {
        putchar('0');
        return;
    }
    
    char buffer[20];
    int i = 0;
    int negative = 0;
    
    if (num < 0) {
        negative = 1;
        num = -num;
    }
    
    while (num > 0) {
        buffer[i++] = '0' + (num % 10);
        num /= 10;
    }
    
    if (negative) putchar('-');
    
    for (int j = i - 1; j >= 0; j--) {
        putchar(buffer[j]);
    }
}

// Função para limpar tela
void clear_screen() {
    uint16_t *video = (uint16_t*)VIDEO_MEMORY;
    for (int i = 0; i < SCREEN_WIDTH * SCREEN_HEIGHT; i++) {
        video[i] = (0x0F << 8) | ' ';
    }
    cursor_x = 0;
    cursor_y = 0;
}

// Função para simular entrada do teclado (para demonstração)
// Em um sistema real, usaríamos interrupções BIOS
char getchar_demo() {
    // Array de entradas simuladas para demonstração
    static char demo_input[] = "1\nJoao Silva\n25\n12345678901\n2\n3\nNotebook\n150000\n10\n4\n5\n6\n7\n";
    static int demo_index = 0;
    
    if (demo_input[demo_index] != '\0') {
        char c = demo_input[demo_index++];
        putchar(c); // Eco na tela
        return c;
    }
    
    // Se acabou a demo, retorna '7' para sair
    putchar('7');
    putchar('\n');
    return '7';
}

// Função para ler string do usuário
void read_string(char* buffer, int max_len) {
    print("[DEMO MODE] ");
    int i = 0;
    char c = '\0'; // Inicializar para evitar warning
    
    while (i < max_len - 1) {
        c = getchar_demo();
        
        if (c == '\r' || c == '\n') {
            break;
        } else if (c == '\b' && i > 0) {
            i--;
        } else if (c >= 32 && c <= 126) {
            buffer[i++] = c;
        }
    }
    
    buffer[i] = '\0';
    if (c != '\n') putchar('\n');
}

// Função para ler número
int read_int() {
    char buffer[10];
    read_string(buffer, 10);
    
    int result = 0;
    int i = 0;
    int negative = 0;
    
    if (buffer[0] == '-') {
        negative = 1;
        i = 1;
    }
    
    while (buffer[i] >= '0' && buffer[i] <= '9') {
        result = result * 10 + (buffer[i] - '0');
        i++;
    }
    
    return negative ? -result : result;
}

// Função para pausar (simula pressionar tecla)
void pause() {
    print("Pressione qualquer tecla para continuar...");
    getchar_demo();
}

// Funções do mainframe
void adicionar_pessoa() {
    if (num_pessoas >= 50) {
        print("Limite de pessoas atingido!\n");
        return;
    }
    
    clear_screen();
    print("=== ADICIONAR PESSOA ===\n\n");
    
    print("Nome: ");
    read_string(pessoas[num_pessoas].nome, 30);
    
    print("Idade: ");
    pessoas[num_pessoas].idade = read_int();
    
    print("CPF (apenas numeros): ");
    read_string(pessoas[num_pessoas].cpf, 12);
    
    pessoas[num_pessoas].ativo = 1;
    num_pessoas++;
    
    print("\nPessoa adicionada com sucesso!\n");
    pause();
}

void listar_pessoas() {
    clear_screen();
    print("=== LISTA DE PESSOAS ===\n\n");
    
    if (num_pessoas == 0) {
        print("Nenhuma pessoa cadastrada.\n");
    } else {
        for (int i = 0; i < num_pessoas; i++) {
            if (pessoas[i].ativo) {
                print("ID: ");
                print_int(i + 1);
                print(" | Nome: ");
                print(pessoas[i].nome);
                print(" | Idade: ");
                print_int(pessoas[i].idade);
                print(" | CPF: ");
                print(pessoas[i].cpf);
                print("\n");
            }
        }
    }
    
    print("\n");
    pause();
}

void adicionar_produto() {
    if (num_produtos >= 50) {
        print("Limite de produtos atingido!\n");
        return;
    }
    
    clear_screen();
    print("=== ADICIONAR PRODUTO ===\n\n");
    
    print("Nome: ");
    read_string(produtos[num_produtos].nome, 30);
    
    print("Preco (em centavos): ");
    produtos[num_produtos].preco = read_int();
    
    print("Quantidade: ");
    produtos[num_produtos].quantidade = read_int();
    
    produtos[num_produtos].ativo = 1;
    num_produtos++;
    
    print("\nProduto adicionado com sucesso!\n");
    pause();
}

void listar_produtos() {
    clear_screen();
    print("=== LISTA DE PRODUTOS ===\n\n");
    
    if (num_produtos == 0) {
        print("Nenhum produto cadastrado.\n");
    } else {
        for (int i = 0; i < num_produtos; i++) {
            if (produtos[i].ativo) {
                print("ID: ");
                print_int(i + 1);
                print(" | Nome: ");
                print(produtos[i].nome);
                print(" | Preco: ");
                print_int(produtos[i].preco);
                print(" centavos | Qtd: ");
                print_int(produtos[i].quantidade);
                print("\n");
            }
        }
    }
    
    print("\n");
    pause();
}

void salvar_dados() {
    clear_screen();
    print("=== SALVANDO DADOS ===\n\n");
    print("Simulando gravacao em disco...\n");
    
    // Simular processo de escrita
    for (int i = 0; i < 5; i++) {
        print(".");
        // Delay simples
        for (volatile int j = 0; j < 1000000; j++);
    }
    
    print("\nDados salvos com sucesso!\n");
    print("Total de pessoas: ");
    print_int(num_pessoas);
    print("\nTotal de produtos: ");
    print_int(num_produtos);
    print("\n\n(Em implementacao real, gravaria em setores do disco)\n\n");
    pause();
}

void carregar_dados() {
    clear_screen();
    print("=== CARREGANDO DADOS ===\n\n");
    print("Simulando leitura do disco...\n");
    
    // Simular processo de leitura
    for (int i = 0; i < 5; i++) {
        print(".");
        // Delay simples
        for (volatile int j = 0; j < 1000000; j++);
    }
    
    print("\nDados carregados com sucesso!\n");
    print("(Em implementacao real, leria setores do disco)\n\n");
    pause();
}

void mostrar_menu() {
    clear_screen();
    print("=========================\n");
    print("   SISTEMA MAINFRAME     \n");
    print("=========================\n\n");
    print("1. Adicionar Pessoa\n");
    print("2. Listar Pessoas\n");
    print("3. Adicionar Produto\n");
    print("4. Listar Produtos\n");
    print("5. Salvar Dados\n");
    print("6. Carregar Dados\n");
    print("7. Sair\n\n");
    print("Escolha uma opcao (1-7): ");
}

// Função principal do kernel
void kernel_main() {
    clear_screen();
    print("========================================\n");
    print("      SISTEMA MAINFRAME v1.0           \n");
    print("   Boot realizado com sucesso!         \n");
    print("========================================\n\n");
    print("MODO DEMONSTRACAO ATIVO\n");
    print("(Entrada automatica para testes)\n\n");
    pause();
    
    int opcao;
    
    while (1) {
        mostrar_menu();
        opcao = read_int();
        
        switch (opcao) {
            case 1:
                adicionar_pessoa();
                break;
            case 2:
                listar_pessoas();
                break;
            case 3:
                adicionar_produto();
                break;
            case 4:
                listar_produtos();
                break;
            case 5:
                salvar_dados();
                break;
            case 6:
                carregar_dados();
                break;
            case 7:
                clear_screen();
                print("========================================\n");
                print("      ENCERRANDO SISTEMA...            \n");
                print("========================================\n\n");
                print("Estatisticas finais:\n");
                print("- Pessoas cadastradas: ");
                print_int(num_pessoas);
                print("\n- Produtos cadastrados: ");
                print_int(num_produtos);
                print("\n\nObrigado por usar o Sistema Mainframe!\n");
                print("Sistema sera finalizado em 3 segundos...\n");
                
                // Delay antes de finalizar
                for (volatile int i = 0; i < 10000000; i++);
                
                while(1) {
                    // Loop infinito - sistema "desligado"
                    for (volatile int i = 0; i < 1000000; i++);
                }
            default:
                clear_screen();
                print("========================================\n");
                print("         OPCAO INVALIDA!               \n");
                print("========================================\n\n");
                print("Por favor, escolha uma opcao entre 1-7.\n\n");
                pause();
        }
    }
}

// Ponto de entrada (chamado pelo bootloader)
void _start() {
    kernel_main();
}