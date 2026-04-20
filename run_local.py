"""
로컬 테스트용 실행 스크립트
.env 파일에서 환경변수를 로드한 후 main.py 실행

사용법:
  1. .env.example을 .env로 복사
  2. .env에 실제 값 입력
  3. python run_local.py
"""
import os


def load_env():
    """간단한 .env 로더 (python-dotenv 없이)"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        print("❌ .env 파일이 없습니다. .env.example을 복사하여 .env를 만드세요.")
        return False

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

    print("✅ .env 환경변수 로드 완료")
    return True


if __name__ == "__main__":
    if load_env():
        from main import run
        run()
