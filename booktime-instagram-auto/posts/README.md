# Pasta de Posts

Cada subpasta aqui dentro é um post pendente. Quando o workflow rodar, ele:

1. Pega a próxima subpasta em ordem alfabética
2. Publica a imagem + caption.txt
3. Move a subpasta pra `posts/published/`

## Estrutura de cada post

```
posts/
└── 2026-05-15-livro-fulano/
    ├── imagem.jpg       (ou .png)
    └── caption.txt      (texto da legenda)
```

## Dica de nomenclatura

Use prefixo de data pra a ordem ficar clara:
- `2026-05-15-livro-x/`
- `2026-05-16-livro-y/`

Assim, alfabeticamente o mais antigo sempre vem primeiro.
