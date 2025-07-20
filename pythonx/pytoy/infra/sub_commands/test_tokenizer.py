import pytest
from tokenizer import tokenize, Token


def test_basic_tokenization():
    cmd = 'mycmd --input=abc --flag --output "some file.txt"'
    tokens = tokenize(cmd)
    raw_tokens = [t.value for t in tokens]
    assert raw_tokens == ['mycmd', '--input=abc', '--flag', '--output', 'some file.txt']
    assert tokens[0].start == 0
    assert tokens[-1].value == 'some file.txt'

def test_quoted_token():
    cmd = 'mycmd "quoted value"'
    tokens = tokenize(cmd)
    assert len(tokens) == 2
    assert tokens[1].value == 'quoted value'
    assert tokens[1].start < tokens[1].end

def test_repeated_option():
    cmd = 'cmd --flag --flag'
    tokens = tokenize(cmd)
    assert tokens[1].value == '--flag'
    assert tokens[2].value == '--flag'
    assert tokens[1].start != tokens[2].start  

def test_equals_sign():
    cmd = 'tool --opt=value'
    tokens = tokenize(cmd)
    assert tokens[1].value == '--opt=value'
    assert '--opt' in tokens[1].value
    assert '=' in tokens[1].value


if __name__ == "__main__":
    test_basic_tokenization()
    test_quoted_token()
    test_repeated_option()
    test_equals_sign()
