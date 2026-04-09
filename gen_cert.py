from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

def generate_self_signed_cert():
    # 1. Private Key Banao
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    # 2. Details Bharo
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"IN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Gujarat"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Ahmedabad"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"TrafficAI Corp"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    
    # 3. Certificate Sign karo
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.datetime.utcnow()).not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365)).add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False).sign(key, hashes.SHA256())
    
    # 4. Files Save karo
    with open("cert.pem", "wb") as f: f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open("key.pem", "wb") as f: f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    
    print("✅ Security Certificates Generated: cert.pem & key.pem")

if __name__ == "__main__":
    try:
        generate_self_signed_cert()
    except ImportError:
        print("⚠️ 'cryptography' library missing. Run: pip install cryptography")