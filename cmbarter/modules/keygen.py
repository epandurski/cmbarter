## The author disclaims copyright to this source code.  In place of
## a legal notice, here is a poem:
##
##   "Metaphysics"
##   
##   Matter: is the music 
##   of the space.
##   Music: is the matter
##   of the soul.
##   
##   Soul: is the space
##   of God.
##   Space: is the soul
##   of logic.
##   
##   Logic: is the god
##   of the mind.
##   God: is the logic
##   of bliss.
##   
##   Bliss: is a mind
##   of music.
##   Mind: is the bliss
##   of the matter.
##   
######################################################################
## This file implements the registration key calculation algorithm.
##
import sys, os, getopt, hashlib

# Try to import PyCrypto. If not possible, fallback to pure-python AES
# implementation.
try:
    from Crypto.Cipher import AES
except ImportError:
    from cmbarter.modules import ska_aes

    class MockAES:
        MODE_ECB = None
        block_size = 16
        def new(self, key, mode=None):
            return ska_aes.aes(key)

    AES = MockAES()



CIPHER = AES  # A cryptographically secure block cipher with at least
              # 64-bit block size, and at least 128-bit secret key.



class InvalidCharacter(ValueError):
    pass

    

class SncCode:
    width = 5

    _char_list = u'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # 32 characters
    _char_dict = {}
    for i, c in enumerate(_char_list):
        _char_dict[c] = i

    def chr(self, i):
        return self._char_list[i]
    
    def ord(self, char):
        try:
            return self._char_dict[char]
        except KeyError:
            raise InvalidCharacter()

SNC = SncCode()  # Serial Number Code



class Latin1Code:
    width = 8

    def chr(self, i):
        assert 0 <= i <= 0xff
        return unichr(i)
    
    def ord(self, char):
        i = ord(char)
        assert 0 <= i <= 0xff
        return i

LATIN1 = Latin1Code()



class Keygen:
    """Generates and validates registraton keys.

    >>> gen = Keygen('a secret')
    >>> valid_key = gen.generate(seqnum=0)
    >>> gen.validate(valid_key) == valid_key
    True
    >>> gen.validate(u'\u6234') == ''
    True
    >>> gen.validate('x') == ''
    True
    >>> bool(gen.validate(gen.generate(2**32-1)))
    True
    >>> bool(gen.validate('2QGGXHWT8GZ8SHK5JE5GURF3GE'))
    False
    """

    def __init__(self, secret):
        m = hashlib.md5()
        m.update(secret.encode('utf-8'))
        self.cipher = CIPHER.new(m.digest(), CIPHER.MODE_ECB)
        self.block_width = 8 * CIPHER.block_size


    def _encode(self, i, code):
        mask = 2**code.width - 1
        chars, shift = [], 0
        while shift < self.block_width:
            chars.append(code.chr((i >> shift) & mask))
            shift += code.width
        return u''.join(chars).encode('latin-1')


    def _decode(self, s, code):
        s = s.decode('latin-1')
        i, weight = 0, 1
        for c in s:
            i += code.ord(c) * weight
            weight <<= code.width
        return i


    def generate(self, seqnum):
        assert 0 <= seqnum <= 0xffffffff
        block = self._encode(seqnum, LATIN1)
        block = self.cipher.encrypt(block)
        return self._encode(self._decode(block, LATIN1), SNC).decode('ascii')


    def validate(self, s):
        try:
            block = self._encode(self._decode(s.encode('ascii'), SNC), LATIN1)
            block = self.cipher.decrypt(block)
            i = self._decode(block, LATIN1)
            if 0 <= i <= 0xffffffff:
                return self.generate(i)  # Returns the canonical representation of the key
        except (InvalidCharacter, UnicodeError):
            pass

        return u''  # Invalid key



if __name__ == '__main__':
    import doctest
    doctest.testmod()
