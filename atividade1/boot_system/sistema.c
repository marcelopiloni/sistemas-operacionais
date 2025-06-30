#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>

struct Pessoa {
    char nome[50];
    int idade;
    char cpf[15];
};

struct Produto {
    char nome[50];
    int preco;
    int quantidade;
};

struct Pessoa pessoas[50];
struct Produto produtos[50];
int num_pessoas = 0;
int num_produtos = 0;

void salvar_dados() {
    FILE* arquivo = fopen("/home/debian/dados.txt", "w");
    if (arquivo == NULL) {
        printf("Erro ao salvar!\n");
        return;
    }
    
    fprintf(arquivo, "%d\n", num_pessoas);
    for (int i = 0; i < num_pessoas; i++) {
        fprintf(arquivo, "%s,%d,%s\n", pessoas[i].nome, pessoas[i].idade, pessoas[i].cpf);
    }
    
    fprintf(arquivo, "%d\n", num_produtos);
    for (int i = 0; i < num_produtos; i++) {
        fprintf(arquivo, "%s,%d,%d\n", produtos[i].nome, produtos[i].preco, produtos[i].quantidade);
    }
    
    fclose(arquivo);
    printf("Dados salvos!\n");
    getchar();
}

void carregar_dados() {
    FILE* arquivo = fopen("/home/debian/dados.txt", "r");
    if (arquivo == NULL) {
        printf("Arquivo nao encontrado. Iniciando vazio.\n");
        getchar();
        return;
    }
    
    fscanf(arquivo, "%d", &num_pessoas);
    for (int i = 0; i < num_pessoas; i++) {
        fscanf(arquivo, "%s,%d,%s", pessoas[i].nome, &pessoas[i].idade, pessoas[i].cpf);
    }
    
    fscanf(arquivo, "%d", &num_produtos);
    for (int i = 0; i < num_produtos; i++) {
        fscanf(arquivo, "%s,%d,%d", produtos[i].nome, &produtos[i].preco, &produtos[i].quantidade);
    }
    
    fclose(arquivo);
    printf("Dados carregados!\n");
    getchar();
}

void adicionar_pessoa() {
    if (num_pessoas >= 50) {
        printf("Limite atingido!\n");
        getchar();
        return;
    }
    
    printf("Nome: ");
    scanf("%s", pessoas[num_pessoas].nome);
    printf("Idade: ");
    scanf("%d", &pessoas[num_pessoas].idade);
    printf("CPF: ");
    scanf("%s", pessoas[num_pessoas].cpf);
    
    num_pessoas++;
    printf("Pessoa adicionada!\n");
    while (getchar() != '\n');
    getchar();
}

void listar_pessoas() {
    printf("\n=== PESSOAS ===\n");
    for (int i = 0; i < num_pessoas; i++) {
        printf("%d. %s - %d anos - CPF: %s\n", i+1, pessoas[i].nome, pessoas[i].idade, pessoas[i].cpf);
    }
    printf("\nPressione ENTER...");
    getchar();
}

void adicionar_produto() {
    if (num_produtos >= 50) {
        printf("Limite atingido!\n");
        getchar();
        return;
    }
    
    printf("Nome do produto: ");
    scanf("%s", produtos[num_produtos].nome);
    printf("Preco: ");
    scanf("%d", &produtos[num_produtos].preco);
    printf("Quantidade: ");
    scanf("%d", &produtos[num_produtos].quantidade);
    
    num_produtos++;
    printf("Produto adicionado!\n");
    while (getchar() != '\n');
    getchar();
}

void listar_produtos() {
    printf("\n=== PRODUTOS ===\n");
    for (int i = 0; i < num_produtos; i++) {
        printf("%d. %s - Preco: %d - Qtd: %d\n", i+1, produtos[i].nome, produtos[i].preco, produtos[i].quantidade);
    }
    printf("\nPressione ENTER...");
    getchar();
}

void mostrar_menu() {
    system("clear");
    printf("=== SISTEMA MAINFRAME ===\n");
    printf("1. Adicionar Pessoa\n");
    printf("2. Listar Pessoas\n");
    printf("3. Adicionar Produto\n");
    printf("4. Listar Produtos\n");
    printf("5. Salvar Dados\n");
    printf("6. Carregar Dados\n");
    printf("7. Sair\n");
    printf("Opcao: ");
}

int main() {
    int tty_fd = open("/dev/tty1", O_RDWR);
    if (tty_fd < 0) {
        return 1;
    }
    dup2(tty_fd, STDIN_FILENO);
    dup2(tty_fd, STDOUT_FILENO);
    dup2(tty_fd, STDERR_FILENO);
    
    int opcao;
    carregar_dados();
    
    while (1) {
        mostrar_menu();
        scanf("%d", &opcao);
        
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
                salvar_dados();
                printf("Saindo...\n");
                exit(0);
            default:
                printf("Opcao invalida!\n");
                while (getchar() != '\n');
                getchar();
        }
    }
    
    return 0;
}