/**
 * Abstract Syntax Tree (AST) Code Clone Normalization Engine.
 * Tokenizes source code, abstracts identifiers/literals, extracts structural AST node streams,
 * and generates canonical normalized representations for Types 1-4 code clone detection.
 */

export interface ASTNode {
  type: string;
  value?: string;
  children: ASTNode[];
  startPos: number;
  endPos: number;
}

export interface NormalizedASTResult {
  rawCode: string;
  normalizedCode: string;
  tokens: string[];
  nodeCount: number;
  depth: number;
}

export class ASTCodeCloneNormalizer {
  private identifierMap: Map<string, string>;
  private identifierCounter: number;

  constructor() {
    this.identifierMap = new Map();
    this.identifierCounter = 0;
  }

  public resetNormalizationMap(): void {
    this.identifierMap.clear();
    this.identifierCounter = 0;
  }

  public tokenize(code: string): string[] {
    const cleanCode = code.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '');
    const tokenRegex = /[a-zA-Z_]\w*|\d+(?:\.\d+)?|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[{}()\[\];,.<>+\-*\/=|^&%!?]/g;
    return cleanCode.match(tokenRegex) || [];
  }

  public normalizeTokens(tokens: string[]): string[] {
    this.resetNormalizationMap();
    const keywords = new Set([
      'function', 'var', 'let', 'const', 'if', 'else', 'for', 'while',
      'return', 'class', 'import', 'export', 'from', 'try', 'catch', 'throw',
      'async', 'await', 'new', 'this', 'typeof', 'instanceof'
    ]);

    return tokens.map(token => {
      if (keywords.has(token)) {
        return token;
      }
      if (/^[a-zA-Z_]\w*$/.test(token)) {
        if (!this.identifierMap.has(token)) {
          this.identifierMap.set(token, `VAR_${this.identifierCounter++}`);
        }
        return this.identifierMap.get(token)!;
      }
      if (/^\d+(?:\.\d+)?$/.test(token)) {
        return 'LIT_NUM';
      }
      if (/^["'].*["']$/.test(token)) {
        return 'LIT_STR';
      }
      return token;
    });
  }

  public parsePseudoAST(tokens: string[]): ASTNode {
    const root: ASTNode = { type: 'Program', children: [], startPos: 0, endPos: tokens.length };
    let currentParent = root;
    const stack: ASTNode[] = [root];

    tokens.forEach((token, index) => {
      if (token === '{' || token === '(') {
        const blockNode: ASTNode = {
          type: token === '{' ? 'BlockStatement' : 'GroupExpression',
          children: [],
          startPos: index,
          endPos: index
        };
        currentParent.children.push(blockNode);
        stack.push(blockNode);
        currentParent = blockNode;
      } else if (token === '}' || token === ')') {
        if (stack.length > 1) {
          const closedNode = stack.pop()!;
          closedNode.endPos = index;
          currentParent = stack[stack.length - 1];
        }
      } else {
        currentParent.children.push({
          type: 'TokenNode',
          value: token,
          children: [],
          startPos: index,
          endPos: index
        });
      }
    });

    return root;
  }

  public calculateASTDepth(node: ASTNode): number {
    if (node.children.length === 0) return 1;
    let maxChildDepth = 0;
    node.children.forEach(child => {
      const d = this.calculateASTDepth(child);
      if (d > maxChildDepth) maxChildDepth = d;
    });
    return maxChildDepth + 1;
  }

  public countNodes(node: ASTNode): number {
    let count = 1;
    node.children.forEach(child => {
      count += this.countNodes(child);
    });
    return count;
  }

  public normalizeCode(rawCode: string): NormalizedASTResult {
    const tokens = this.tokenize(rawCode);
    const normalizedTokens = this.normalizeTokens(tokens);
    const ast = this.parsePseudoAST(normalizedTokens);

    return {
      rawCode,
      normalizedCode: normalizedTokens.join(' '),
      tokens: normalizedTokens,
      nodeCount: this.countNodes(ast),
      depth: this.calculateASTDepth(ast)
    };
  }
}
