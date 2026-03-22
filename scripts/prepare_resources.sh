#!/bin/bash
# Resource Preparation Script for Xiangqi Hybrid Agent
# This script helps download and set up resources for Sprint 2.1

set -e

echo "======================================"
echo "Xiangqi Hybrid Agent - Resource Setup"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

echo "Detected OS: $OS ($ARCH)"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ============================================
# 1. Setup Pikafish Engine
# ============================================
setup_engine() {
    echo -e "${YELLOW}[1/4] Setting up Pikafish Engine...${NC}"

    if [ -f "data/engine/pikafish" ] || [ -f "data/engine/pikafish.exe" ]; then
        echo -e "${GREEN}✓ Pikafish already exists${NC}"
        return
    fi

    echo "Downloading Pikafish..."
    cd data/engine

    case "$OS" in
        Linux)
            if [ "$ARCH" = "x86_64" ]; then
                DOWNLOAD_URL="https://github.com/official-pikafish/Pikafish/releases/download/v2024.08.05/pikafish-bmi2-linux.tar.bz2"
            else
                DOWNLOAD_URL="https://github.com/official-pikafish/Pikafish/releases/download/v2024.08.05/pikafish-modern-linux.tar.bz2"
            fi
            ;;
        Darwin)
            if [ "$ARCH" = "arm64" ]; then
                DOWNLOAD_URL="https://github.com/official-pikafish/Pikafish/releases/download/v2024.08.05/pikafish-bmi2-apple.tar.bz2"
            else
                DOWNLOAD_URL="https://github.com/official-pikafish/Pikafish/releases/download/v2024.08.05/pikafish-modern-mac.tar.bz2"
            fi
            ;;
        *)
            echo -e "${RED}✗ Unsupported OS: $OS${NC}"
            echo "Please download manually from: https://github.com/official-pikafish/Pikafish/releases"
            cd ../..
            return
            ;;
    esac

    curl -L -o pikafish.tar.bz2 "$DOWNLOAD_URL"
    tar -xjf pikafish.tar.bz2
    chmod +x pikafish
    rm pikafish.tar.bz2

    cd ../..

    echo -e "${GREEN}✓ Pikafish installed${NC}"
    echo ""
}

# ============================================
# 2. Setup Neo4j (Docker)
# ============================================
setup_neo4j() {
    echo -e "${YELLOW}[2/4] Setting up Neo4j Database...${NC}"

    if ! command_exists docker; then
        echo -e "${RED}✗ Docker not installed${NC}"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        return
    fi

    if docker ps | grep -q xiangqi-neo4j; then
        echo -e "${GREEN}✓ Neo4j container already running${NC}"
        return
    fi

    echo "Starting Neo4j container..."
    docker run -d \
        --name xiangqi-neo4j \
        -p 7474:7474 \
        -p 7687:7687 \
        -e NEO4J_AUTH=neo4j/xiangqi123 \
        -v "$(pwd)/data/graph_db:/data" \
        neo4j:latest

    echo -e "${GREEN}✓ Neo4j started${NC}"
    echo "  Browser: http://localhost:7474"
    echo "  Username: neo4j"
    echo "  Password: xiangqi123"
    echo ""
}

# ============================================
# 3. Check Chess Books
# ============================================
setup_books() {
    echo -e "${YELLOW}[3/4] Checking Chess Books...${NC}"

    BOOK_COUNT=$(find data/books -name "*.pdf" 2>/dev/null | wc -l)

    if [ "$BOOK_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $BOOK_COUNT PDF book(s)${NC}"
        ls -lh data/books/*.pdf
    else
        echo -e "${YELLOW}! No PDF books found${NC}"
        echo "Please add chess books to data/books/ directory"
        echo "Note: Ensure copyright compliance"
    fi
    echo ""
}

# ============================================
# 4. Check Game Databases
# ============================================
setup_games() {
    echo -e "${YELLOW}[4/4] Checking Game Databases...${NC}"

    GAME_COUNT=$(find data/games -name "*.pgn" 2>/dev/null | wc -l)

    if [ "$GAME_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $GAME_COUNT PGN file(s)${NC}"
        ls -lh data/games/*.pgn
    else
        echo -e "${YELLOW}! No PGN files found${NC}"
        echo "Please add game databases to data/games/ directory"
    fi
    echo ""
}

# ============================================
# Main Menu
# ============================================
echo "What would you like to do?"
echo ""
echo "  1) Setup everything (engine + Neo4j + check resources)"
echo "  2) Setup engine only"
echo "  3) Setup Neo4j only"
echo "  4) Check resources (books + games)"
echo "  5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case "$choice" in
    1)
        setup_engine
        setup_neo4j
        setup_books
        setup_games
        ;;
    2)
        setup_engine
        ;;
    3)
        setup_neo4j
        ;;
    4)
        setup_books
        setup_games
        ;;
    5)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}======================================"
echo "Setup Complete!"
echo "======================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Copy config/settings.yaml.example to config/settings.yaml"
echo "  2. Edit settings.yaml with your preferences"
echo "  3. Add chess books (PDF) to data/books/"
echo "  4. Add game databases (PGN) to data/games/"
echo "  5. Run: python scripts/vectorize_books.py (Sprint 2.1)"
echo "  6. Run: python scripts/import_to_neo4j.py (Sprint 2.1)"
echo ""
