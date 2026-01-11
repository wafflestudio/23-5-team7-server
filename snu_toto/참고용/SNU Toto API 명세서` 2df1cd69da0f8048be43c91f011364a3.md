# SNU Toto API 명세서`

상태: 진행중

## 0. 설계 변경: 초기 ERD의 한계

제공된 초기 ERD(`option_a`, `option_b` 컬럼 방식)는 다음과 같은 한계가 있어 **테이블 구조 변경(EventOption 도입)**을 제안합니다.

### 1) 시스템적 한계점

1. **"무승부" 베팅 불가능**: ERD상 `Event` 결과에는 `DRAW`가 있으나, 유저 베팅(`Betting`)은 A/B 둘 중 하나만 선택(`selected_option`) 가능합니다. 축구 경기 등에서 무승부 예측이 불가능합니다.
2. **확장성 부족**: 선택지가 2개로 고정(`option_a`, `option_b`)되어 있어, 추후 '3파전'이나 '객관식 퀴즈' 등의 이벤트 확장이 불가능합니다.

### 2) 해결 방안 (본 명세서 반영)

- 기존 와팡 과제의 `Store`(1) : `Product`(N) 구조를 차용하여 **`Event`(1) : `EventOption`(N)** 구조로 정규화합니다.
- 이를 통해 무승부 옵션 생성 및 N개의 선택지 확장이 가능해집니다.

---

## 1. 데이터베이스 모델 설계

[**ER Diagram**](https://www.erdcloud.com/d/WhWihZ7TCyWtsezf6)

### 1) Users (유저)

- `user_id` (UUID, PK)
- `email` (SNU 메일, Unique)
- `hashed_password`
- `nickname`  (Unique)
- `points` (Integer, Default 10000)
- `role` (Enum: USER, ADMIN)
- `is_verified` (Boolean, Default false)
- `created_at` (Datetime)

### 2) Events (이벤트)

- `event_id` (UUID, PK)
- `creator_id` (UUID, FK -> Users)
- `title`, `description`
- `status` (Enum: READY, OPEN, CLOSED, SETTLED, CANCELLED)
- `created_at` (Datetime)
- `start_at` (Datetime)
- `end_at` (Datetime)
- *(option_a, option_b 컬럼 제거 -> EventOption 테이블로 분리)*

### 3) Event_options (이벤트 선택지 - 신규 추가)

- **`option_id`** (UUID, PK)
- `event_id` (UUID, FK -> Event)
- **`name`** (Varchar): 옵션 명 (예: "공대 승", "자연대 승", "무승부")
- `order` 옵션 순서(zero-based)
- `~~total_bet_amount` (Integer): 해당 옵션에 걸린 총 액수~~
- `option_total_amount` (Integer): 해당 옵션에 걸린 총 액수
- `is_winner` 승리여부
- **`~~current_odds`** (Float): 현재 배당률 (계산 필드, API 응답 시 포함)~~
- `participant_count`(int): 현재 참여 인원
- `bet_id` (UUID, PK)
- `user_id` (FK), `event_id` (FK)
- **`selected_option_id`** (UUID, FK -> EventOption): 기존 A/B Enum 대신 옵션 ID 참조
- `amount` (Integer)
- `status` (Enum: PENDING, WIN, LOSE, REFUND)
- `created_at` (Datetime)

### 5) 기타 (그대로 유지)

- **Point_history**, **Event_images**

---

## 2. API 구현

### 1. `/api/auth` & `/api/users` 엔드포인트

### 1-1) POST `/api/users` — 회원가입(일반/소셜 공통)

사용자의 가입 요청을 받아 검증 후 저장합니다. 초기 가입 시 `is_snu_verified`와 `is_verified`는 모두 `False`로 설정됩니다.

`is_snu_verified`가 `False`로 설정된 사용자는 로그인을 할 수 없습니다. 회원가입 직후 스누메일 인증 로직으로 이동합니다. (만약 회원가입 직후 인증을 받지 못하면 로그인이 거부되며, 이때 다시 스누메일을 인증할 수 있습니다.)

**검증 및 처리 규칙:**

- **email**: 필수 필드이며 이메일 형식이어야 합니다. `@snu.ac.kr` 도메인만 허용하며, 기존 유저와 중복될 수 없습니다.
- **password**: 일반 가입(`social_type="LOCAL"`) 시 필수입니다. **8자 이상 20자 이하**여야 하며 **Argon2**로 해싱 저장합니다.
- **nickname**: 필수 필드이며 **2자 이상 20자 이하**여야 합니다. 기존 유저와 중복될 수 없습니다.
- **social_type**: "LOCAL", "GOOGLE", "KAKAO" 중 하나여야 합니다. (기본값 "LOCAL")
- **social_id**: 소셜 가입 시 필수이며, 해당 타입 내에서 고유해야 합니다.
- **요청**
    
    ```json
    {
        "email": "waffle@snu.ac.kr",
        "password": "password1234",
        "nickname": "토토왕",
        "social_type": "LOCAL",
    	  "social_id": null
    }
    ```
    
- **성공 응답 (201 Created)**
    
    ```json
    {
        "user_id": "uuid...",
        "email": "waffle@snu.ac.kr",
        "points": 10000,
        "role": "USER",
        "is_snu_verified": false,
    	  "is_verified": false,
    	  "social_type": "LOCAL",
    	  "created_at": "2026-01-09T01:20:00Z"
    }
    
    ```
    
- **실패 응답**
    
    
    | **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
    | --- | --- | --- | --- |
    | 400 | `ERR_001` | MISSING REQUIRED FIELDS | 필수 요청 필드가 누락됨 |
    | 400 | `ERR_002` | INVALID FIELD FORMAT | 필드 형식이 올바르지 않음 (이메일 형식 등) |
    | 409 | `ERR_006` | EMAIL ALREADY EXISTS | 회원가입 시 이미 존재하는 이메일 |
    | 409 | `ERR_007` | NICKNAME ALREADY EXISTS | 회원가입 시 이미 존재하는 닉네임 |
    | 403 | `ERR_010` | ONLY SNU EMAIL ALLOWED | 이메일이 @snu.ac.kr 도메인이 아닌 경우 |
    | 400 | `ERR_016` | PASSWORD IS REQUIRED FOR LOCAL SIGNUP | 로컬 회원가입에서 password가 누락됨 |
    | 400 | `ERR_017` | SOCIAL ID IS REQUIRED FOR SOCIAL SIGNUP | 소셜 회원가입에서 소셜 ID가 누락됨 |
    | 409 | `ERR_018` | SOCIAL ID ALREADY EXISTS | 이미 가입된 소셜 ID |

### 1-2) GET `/api/auth/google/login` — 소셜 로그인 시작

사용자를 구글 OAuth2 인증 페이지로 리다이렉트시킵니다.

### 1-3) GET `/api/auth/google/callback` — 소셜 로그인 콜백

구글 인증 성공 후 전달받은 `code`를 사용하여 유저 정보를 획득하고 로그인 또는 회원가입 절차를 진행합니다.

**검증 및 처리 규칙:**

- **이메일 도메인 체크**: 구글로부터 받은 이메일이 `@snu.ac.kr`이 아닌 경우 가입/로그인을 거부합니다.
- **기존 유저 판별**: `social_id`가 DB에 존재하면 즉시 로그인을 처리(JWT 발급)합니다.
- **신규 유저 판별**: `social_id`가 DB에 없으면 회원가입을 위해 구글에서 획득한 정보를 반환하며, 프론트엔드에서 닉네임 설정 페이지로 유도합니다. 이후 POST `/api/users` 를 통해 가입을 회원가입을 완료합니다.

- **요청**
    - `code` : 구글 인증 서버에서 발급한 인가 코드
- **성공 응답 1 (200 OK)**
    
    ```json
    {
        "message": "로그인 성공",
        "needs_signup": false,
        "access_token": "jwt_access_token...",
        "refresh_token": "jwt_refresh_token...",
        "user": {
            "email": "waffle@snu.ac.kr",
            "nickname": "토토왕",
            "is_snu_verified": true
        }
    }
    ```
    
- **성공 응답 2: 신규 유저 (200 OK)**
    
    ```json
    {
        "message": "신규 유저입니다. 가입을 위해 닉네임을 입력해주세요.",
        "needs_signup": true,
        "email": "waffle@snu.ac.kr",
        "social_id": "google_sub_12345...",
        "social_type": "GOOGLE"
    }
    ```
    
- **실패 응답**
    
    
    | **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
    | --- | --- | --- | --- |
    | 409 | `ERR_006` | EMAIL ALREADY EXISTS | 회원가입 시 이미 존재하는 이메일 |
    | 403 | `ERR_010` | ONLY SNU EMAIL ALLOWED | 이메일이 @snu.ac.kr 도메인이 아닌 경우 |
    | 400 | `ERR_019` | GOOGLE AUTH FAILED | 구글 서버와의 통신 중 오류 발생 (인가 코드 만료 등) |
    | 400 | `ERR_020` | INVALID CALLBACK REQUEST | 필수 쿼리 파라미터(code)가 누락된 경우 |

### 1-4) POST `/api/auth/verify-email/send` — 인증번호 발송

가입한 이메일로 6자리 인증 코드를 발송합니다.

- **헤더**
`Authorization: Bearer <Verification_Token>` (로그인 시 발급된 임시 토큰)
- **요청**
    
    없음
    
- **응답 (200 OK)**
    
    ```json
    {
      "message": "인증번호가 가입하신 이메일로 전송되었습니다."
    }
    ```
    
- **실패 응답**
    
    
    | **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
    | --- | --- | --- | --- |
    | 400 | `ERR_003` | BAD AUTHORIZATION HEADER | Authorization 헤더 형식이 잘못됨 |
    | 401 | `ERR_004` | UNAUTHENTICATED | Authorization 헤더가 없음 |
    | 401 | `ERR_005` | INVALID TOKEN | 유효하지 않거나 만료된 토큰 |
    | 400 | `ERR_011` | EMAIL ALREADY VERIFIED | 이미 인증이 완료된 이메일 |
    | 500 | `ERR_013` | FAILED TO SEND EMAIL | 인증 메일 전송 실패 |
    | 429 | `ERR_021` | TOO MANY REQUESTS | 인증 메일 재발송 간격(1분) 미달 |

### 1-5) POST `/api/auth/verify-email/confirm` — 인증 코드 확인

사용자가 입력한 코드를 검증하고 `is_snu_verified`를 `True`로 변경합니다.

- **헤더**
`Authorization: Bearer <Verification_Token>` (로그인 시 발급된 임시 토큰)
- **요청**
    
    ```json
    {
      "code": "123456"
    }
    ```
    
- **응답 (200 OK)**
    
    ```json
    {
    	"email": "student@snu.ac.kr",
      "is_snu_verified": true,
      "message": "이메일 인증이 완료되었습니다. 다시 로그인해주세요."
    }
    ```
    
- **실패 응답**
    
    
    | **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
    | --- | --- | --- | --- |
    | 400 | `ERR_003` | BAD AUTHORIZATION HEADER | Authorization 헤더 형식이 잘못됨 |
    | 401 | `ERR_004` | UNAUTHENTICATED | Authorization 헤더가 없음 |
    | 401 | `ERR_005` | INVALID TOKEN | 유효하지 않거나 만료된 토큰 |
    | 400 | `ERR_012` | INVALID VERIFICATION CODE | 이메일 인증 코드가 틀린 경우, 이메일 인증 시간이 초과된 경우 (5분 경과) |

### 1-6) POST `/api/auth/login` — 로그인

- **일반 로그인**: `email`과 `password`를 대조하여 검증합니다.

- **요청**
    
    ```jsx
    {
      "email": "waffle@snu.ac.kr",
      "password": "password1234"
    }
    ```
    
- **성공 응답 (200 OK)**
    
    ```json
    {
        "access_token": "...",
        "refresh_token": "...",
        "user": { 
    	    "user_id": "...",
    	    "nickname": "토토왕",
    			"is_snu_verified": true,
    			"points": 10000
    		}
    }
    ```
    
- **응답(이메일 인증 필요)**
- 임시 토큰(`verification_token`) 포함
    
    ```json
    {
        "error_code": "ERR_015",
        "error_msg": "EMAIL VERIFICATION REQUIRED",
        "verification_token": "..." 
    }
    ```
    
- **실패 응답**
    
    
    | **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
    | --- | --- | --- | --- |
    | 400 | `ERR_001` | MISSING REQUIRED FIELDS | 필수 요청 필드가 누락됨 |
    | 401 | `ERR_014` | INVALID CREDENTIALS | 이메일이 없거나 비밀번호가 틀린 경우 (보안상 통합) |
    | 403 | `ERR_015` | EMAIL VERIFICATION REQUIRED | 계정은 있으나 아직 SNU 메일 인증을 안 한 사용자가 로그인 시도 |

### 2. `/api/events` 엔드포인트 (핵심 기능 1 + 개선안)

### 2-1) POST `/api/events` — 이벤트 생성 (로그인 필요)

- 사용자가 새로운 이벤트를 생성하며, **옵션 리스트**를 함께 정의합니다.

**검증 및 처리 규칙:**

- **title**: 필수 필드이며 **5자 이상 100자 이하**여야 합니다.
- **description**: 선택 필드이며 이벤트에 대한 상세 설명을 텍스트로 입력합니다.
- **end_at**: 필수 필드이며 현재 시각보다 미래의 시각이어야 합니다.
- **options**: 필수 필드이며 **2개 이상 10개 이하**의 선택지 객체를 포함해야 합니다.
    - **options[].name**: 필수이며 **1자 이상 50자 이하**여야 합니다. 한 이벤트 내에서 다른 옵션과 이름이 중복될 수 없습니다.
    - **options[].order**: 필수이며 **0 이상의 정수**여야 합니다. 선택지가 화면에 노출되는 순서를 결정합니다.
- **images**: 선택 필드이며 이미지 객체 리스트를 포함할 수 있습니다.
    - **images[].image_url**: 필수이며 유효한 HTTP/HTTPS URL 형식이어야 합니다.
    - **images[].display_order**: 필수이며 **0 이상의 정수**여야 합니다.
    
- **요청**
    
    ```json
    {
        "title": "공대 vs 자연대 축구",
        "description": "관악의 주인 결정전",
        "end_at": "2024-05-20T18:00:00",
        "options": [
            { "name": "공대 승", "order": 0 },
            { "name": "자연대 승", "order": 1 },
            { "name": "무승부", "order": 2 }
        ],
        "images": [
            { "image_url": "https://s3.aws.com/snu-toto/event1-1.jpg", "display_order": 0 }
        ]
    }
    
    ```
    
- **응답 (201 Created)**
    
    ```json
    {
        "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "creator_id": "7ca32b1a-1234-4567-8901-abcdef123456",
        "title": "공대 vs 자연대 축구",
        "description": "관악의 주인 결정전",
        "status": "READY",
        "created_at": "2026-01-11T03:52:00Z",
        "end_at": "2026-05-20T18:00:00Z",
        "options": [
            {
                "option_id": "opt-9876-5432-10",
                "name": "공대 승",
                "order": 0,
                "participant_count": 0,
                "option_total_amount": 0,
                "is_winner": null
            },
            ...
        ],
        "images": [
            {
                "image_id": "img-1111-2222",
                "image_url": "https://s3.aws.com/snu-toto/event1.jpg",
                "display_order": 0
            }
        ]
    }
    ```
    
- **실패 응답**
    
    
    | **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
    | --- | --- | --- | --- |
    | 400 | `ERR_001` | MISSING REQUIRED FIELDS | 필수 요청 필드가 누락됨 |
    | 400 | `ERR_002` | INVALID FIELD FORMAT | 필드 형식이 올바르지 않음 (이메일 형식 등) |
    | 400 | `ERR_003` | BAD AUTHORIZATION HEADER | Authorization 헤더 형식이 잘못됨 |
    | 401 | `ERR_004` | UNAUTHENTICATED | Authorization 헤더가 없음 |
    | 401 | `ERR_005` | INVALID TOKEN | 유효하지 않거나 만료된 토큰 |
    | 400 | `ERR_023` | INVALID END DATE | 종료시각이 현재시각보다 이전인 경우 |
    | 400 | `ERR_024` | INSUFFICIENT/TOO MANY OPTIONS | 옵션의 개수가 2개 미만 또는 10개 초과일 때 |
    | 400 | `ERR_025` | INVALID OPTION NAME | 옵션 이름이 50자를 초과하거나 공백으로만 이루어진 옵션 이름 |
    | 400 | `ERR_026` | INVALID OPTION ORDER | 옵션의 순서가 음수이거나 정수가 아닐 때 |
    | 400 | `ERR_027` | INVALID IMAGE URL | 이미지 URL이 유효한 형식이 아닐 때 |
    | 409 | `ERR_028` | DUPLICATE OPTION NAME | 한 이벤트 내에 동일한 이름의 옵션이 존재할 때 |

### 2-2) PATCH `/api/events/{event_id}/status` — 상태 변경(로그인 필요)

URL 파라미터로 `event_id`가 들어오며, 이벤트의 상태를 `"READY"`, `"OPEN"`, `"CLOSED"`, `"SETTLED"`, `"CANCELLED"` 중 하나로 변경합니다.

상태를 `"SETTLED"` 로 변경하고자 할 때는 승리 옵션의 ID가 요청에 포함되어야 합니다.

**상태 전이 제한**: 이벤트 상태는 정해진 순서로만 변경 가능합니다.

- **READY → OPEN**: 이벤트가 승인되어 사용자가 베팅할 수 있는 상태로 전환합니다.
- **OPEN → CLOSED**: 베팅을 마감합니다. 더 이상 베팅이 불가능하며 결과 입력을 기다리는 상태입니다.
- **CLOSED → SETTLED**: 결과가 확정되어 당첨자에게 포인트 정산이 완료된 최종 상태입니다. (취소 불가)
- **ANY → CANCELLED**: 이벤트에 문제가 생겨 무효화하는 경우이며, 이미 `SETTLED`된 이벤트는 취소할 수 없습니다.

**권한 검증**: 요청자에게 관리자 권한이 있어야 합니다.

**정산 조건**: `status`를 `"SETTLED"`로 변경하기 전, 반드시 최소 하나 이상의 선택지에 대해 승리 여부(`is_winner=True`)가 먼저 설정되어 있어야 합니다.

- **요청**
    
    ```json
    { 
        "status": "CLOSED",
        "winner_option_id": "opt-uuid-123"
    }
    ```
    
- **응답 (200 OK)**
- **실패 응답**
    
    
    | **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
    | --- | --- | --- | --- |
    | 400 | `ERR_001` | MISSING REQUIRED FIELDS | 필수 요청 필드가 누락됨 |
    | 400 | `ERR_002` | INVALID FIELD FORMAT | 필드 형식이 올바르지 않음 (이메일 형식 등) |
    | 400 | `ERR_003` | BAD AUTHORIZATION HEADER | Authorization 헤더 형식이 잘못됨 |
    | 401 | `ERR_004` | UNAUTHENTICATED | Authorization 헤더가 없음 |
    | 401 | `ERR_005` | INVALID TOKEN | 유효하지 않거나 만료된 토큰 |
    | 400 | `ERR_029` | INVALID STATUS TRANSITION | 잘못된 상태 전이 |
    | 403 | `ERR_030` | NOT ADMIN | 관리자가 아닌 유저가 요청 |
    | 400 | `ERR_031` | NEED WINNER ID | 상태변경시 승리 옵션 ID가 필요 |
    | 400 | `ERR_032` | ALREADY CLOSED | 이미 종료 시각이 지난 이벤트를 오픈하려고 할 때 |
    | 404 | `ERR_033` | WINNER NOT FOUND | 승리 옵션 ID를 해당 이벤트에서 찾을 수 없을 때 |

### 2-3) POST `/api/events/{event_id}/settle` — 결과 정산

- 승리한 옵션의 ID를 지정합니다. (무승부 옵션이 있다면 그것을 선택 가능)
- **요청**
    
    ```json
    { "winner_option_id": "opt-1-uuid..." }
    
    ```
    
- **응답 (200)**
    
    ```json
    {
        "event_id": "...",
        "status": "SETTLED",
        "winner": { "option_id": "opt-1...", "name": "공대 승" },
        "total_payout": 500000
    }
    
    ```
    

---

### 2-4) GET `/api/events/{event_id}` — 이벤트 상세 조회

특정 이벤트의 상세 정보와 해당 이벤트에 포함된 모든 선택지(Options) 및 이미지 정보를 조회.

**기능 설명**

- 이벤트 ID를 경로 파라미터로 받아 해당 데이터가 존재하는지 확인.
- 응답에는 각 옵션별 `total_bet_amount`(총 배팅 금액)가 포함되어 실시간 배팅 현황을 보여줌.

### **1. 요청 (Request)**

- **Method:** `GET`
- **URL:** `/api/events/{event_id}`

### **2. 응답 (Response)**

- **상태 코드:** `200 OK`

JSON

```jsx
{
  "event_id": "7f1c5139-8e80-4d25-b123-446655440000",
  "title": "2026 월드컵 결승전 승자",
  "description": "결승전 승자를 예측하세요",
  "status": "OPEN",
  "total_participants": 50,
  "options": [
    {
      "option_id": "opt-001",
      "name": "브라질",
      "option_total_amount": 15000000,
      "odds": 0.2,
      "is_winner": null
    },
    ...
  ],
  "images": [
    { "image_url": "https://...", "display_order": 0 }
  ]
}
```

---

### 실패 응답 정의

| **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
| --- | --- | --- | --- |
| 404 | `ERR_009` | `EVENT NOT FOUND` | **이벤트를 찾을 수 없는 경우** |

### 2-5) GET `/api/events` — 이벤트 목록 조회

전체 이벤트 목록을 조회하며,  현재는 `status` 쿼리 파라미터를 통해 특정 상태(예: 진행 중인 이벤트)만 필터링하도록 함.

### **요청 (Request)**

- **Method:** `GET`
- **URL:** `/api/events`
- 쿼리 파라미터 사용:
    - `/api/events?status=OPEN`

### **2. 응답 (Response)**

- **성공 응답**
    - **상태 코드:** `200 OK`
    - **본문:** 이벤트 객체 배열

JSON 

```json
[
  {
    "event_id": "7f1c5139-8e80-4d25-b123-446655440000",
    "title": "2026 LCK 스프링 결승전 승리팀은?",
    "description": "승리 할 것 같은 팀을 고르세요",
    "status": "OPEN",
    "total_participants": 50,
    "end_at": "2026-01-15T18:00:00",
    "options": [
      { 
        "option_id": "opt-001", 
        "name": "T1", 
        "option_total_amount": 1500000, 
        "is_winner": null, 
        "participant_count": 30,
        "odds": 1.8
      },
      { 
        "option_id": "opt-002", 
        "name": "Gen.G", 
        "option_total_amount": 1200000, 
        "is_winner": null, 
        "participant_count": 20,
        "odds": 2.25 
      }
    ],
    "images": [
      { "image_url": "https://...", "display_order": 0 }
    ]
  },
  {
    "event_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
    "title": "프리미어리그: 맨시티 vs 리버풀 승자는?",
    "description": "승리 할 것 같은 팀을 고르세요",
    "status": "OPEN",
    "total_participants": 50,
    "end_at": "2026-01-20T21:00:00",
    "options": [
      { 
        "option_id": "opt-101", 
        "name": "맨시티 승리", 
        "option_total_amount": 3200000, 
        "is_winner": null, 
        "participant_count": 22, 
        "odds": 2.17 
      },
      { 
        "option_id": "opt-102", 
        "name": "무승부", 
        "option_total_amount": 850000, 
        "is_winner": null, 
        "participant_count": 6, 
        "odds": 8.18 
      },
      { 
        "option_id": "opt-103", 
        "name": "리버풀 승리", 
        "option_total_amount": 2900000, 
        "is_winner": null, 
        "participant_count": 22, 
        "odds": 2.4 
      }
    ],
    "images": [
      { "image_url": "https://...", "display_order": 0 }
    ]
  }
]
```

### **실패 응답**

| **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
| --- | --- | --- | --- |
| 400 | `ERR_002` | `INVALID FIELD FORMAT` | 필드 형식이 올바르지 않음 |

---

## 3. Betting API — 베팅 관리

사용자가 특정 이벤트의 옵션에 대해 베팅을 생성하고, 자신의 베팅 내역을 조회하는 기능을 제공합니다.

### 3-1) POST `/api/events/{event_id}/bets` — 베팅 생성

사용자가 특정 이벤트의 옵션에 대해 베팅을 생성합니다.

### **1. 요청 (Request)**

- **Method:** `POST`
- **URL:** `/api/events/{event_id}/bets`
- **Headers:** `Authorization: Bearer {access_token}`
- **Body:**
    
    ```json
    {
      "option_id": "opt-001",
      "bet_amount": 10000
    }
    ```
    

### **2. 응답 (Response)**

- **성공 응답**
    - **상태 코드:** `201 Created`
    - **본문:**
        
        ```json
        {
          "bet_id": "bet-7f1c5139-8e80-4d25-b123-446655440000",
          "user_id": "user-123",
          "event_id": "7f1c5139-8e80-4d25-b123-446655440000",
          "option_id": "opt-001",
          "option_name": "브라질",
          "bet_amount": 10000,
          "created_at": "2026-01-09T00:55:00",
          "status": "PENDING"
        }
        ```
        

### **실패 응답**

| **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
| --- | --- | --- | --- |
| 400 | `ERR_001` | `MISSING REQUIRED FIELDS` | 필수 필드(option_id, bet_amount)가 누락된 경우 |
| 400 | `ERR_002` | `INVALID FIELD FORMAT` | bet_amount가 양수가 아니거나 유효하지 않은 경우 |
| 400 | `ERR_011` | `INSUFFICIENT BALANCE` | 사용자의 잔액이 부족한 경우 |
| 404 | `ERR_010` | `EVENT NOT FOUND` | 이벤트를 찾을 수 없는 경우 |
| 404 | `ERR_012` | `OPTION NOT FOUND` | 선택한 옵션을 찾을 수 없는 경우 |
| 409 | `ERR_013` | `EVENT NOT OPEN` | 이벤트가 OPEN 상태가 아닌 경우 (베팅 불가) |
| 409 | `ERR_014` | `DUPLICATE BET` | 사용자가 이미 해당 이벤트에 베팅한 경우 |

---

### 3-2) GET `/api/users/me/bets` — 내 베팅 내역 조회

현재 로그인한 사용자의 전체 베팅 내역을 조회합니다.

### **1. 요청 (Request)**

- **Method:** `GET`
- **URL:** `/api/users/me/bets`
- **Headers:** `Authorization: Bearer {access_token}`
- **Query Parameters (Optional):**
    - `status`: 베팅 상태로 필터링 (예: `PENDING`, `WON`, `LOST`)
    - `limit`: 반환할 최대 개수 (기본값: 20)
    - `offset`: 페이지네이션을 위한 오프셋 (기본값: 0)

### **2. 응답 (Response)**

- **성공 응답**
    - **상태 코드:** `200 OK`
    - **본문:**
        
        ```json
        {
          "total_count": 15,
          "bets": [
            {
              "bet_id": "bet-7f1c5139-8e80-4d25-b123-446655440000",
              "event_id": "7f1c5139-8e80-4d25-b123-446655440000",
              "event_title": "2026 LCK 스프링 결승전 승리팀은?",
              "option_id": "opt-001",
              "option_name": "T1",
              "bet_amount": 10000,
              "potential_payout": 18500,
              "created_at": "2026-01-09T00:55:00",
              "status": "PENDING"
            },
            {
              "bet_id": "bet-a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
              "event_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
              "event_title": "프리미어리그: 맨시티 vs 리버풀",
              "option_id": "opt-102",
              "option_name": "무승부",
              "bet_amount": 5000,
              "potential_payout": 0,
              "created_at": "2026-01-08T15:30:00",
              "status": "LOST",
              "settled_at": "2026-01-08T22:00:00"
            },
            {
              "bet_id": "bet-z9y8x7w6-v5u4-t3s2-r1q0-p9o8n7m6l5k4",
              "event_id": "z9y8x7w6-v5u4-t3s2-r1q0-p9o8n7m6l5k4",
              "event_title": "제98회 아카데미 시상식 작품상 예측",
              "option_id": "opt-201",
              "option_name": "영화 A",
              "bet_amount": 20000,
              "potential_payout": 35000,
              "created_at": "2026-01-05T10:00:00",
              "status": "WON",
              "settled_at": "2026-01-06T08:00:00"
            }
          ]
        }
        ```
        

### **실패 응답**

| **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
| --- | --- | --- | --- |
| 401 | `ERR_015` | `UNAUTHORIZED` | 인증 토큰이 없거나 유효하지 않은 경우 |
| 400 | `ERR_002` | `INVALID FIELD FORMAT` | 잘못된 쿼리 파라미터 형식 |

---

### 3-3) GET `/api/events/{event_id}/bets` — 특정 이벤트의 전체 베팅 조회 (관리자용)

관리자가 특정 이벤트에 대한 모든 사용자의 베팅 내역을 조회합니다.

### **1. 요청 (Request)**

- **Method:** `GET`
- **URL:** `/api/events/{event_id}/bets`
- **Headers:** `Authorization: Bearer {admin_access_token}`

### **2. 응답 (Response)**

- **성공 응답**
    - **상태 코드:** `200 OK`
    - **본문:**
        
        ```json
        {
          "event_id": "7f1c5139-8e80-4d25-b123-446655440000",
          "event_title": "2026 LCK 스프링 결승전 승리팀은?",
          "total_bets": 1520,
          "total_bet_amount": 45000000,
          "bets": [
            {
              "bet_id": "bet-001",
              "user_id": "user-123",
              "option_id": "opt-001",
              "option_name": "T1",
              "bet_amount": 10000,
              "created_at": "2026-01-09T00:55:00",
              "status": "PENDING"
            },
            {
              "bet_id": "bet-002",
              "user_id": "user-456",
              "option_id": "opt-002",
              "option_name": "Gen.G",
              "bet_amount": 15000,
              "created_at": "2026-01-09T01:10:00",
              "status": "PENDING"
            }
          ]
        }
        ```
        

### **실패 응답**

| **상태 코드** | **ERROR_CODE** | **ERROR_MSG** | **상황** |
| --- | --- | --- | --- |
| 401 | `ERR_015` | `UNAUTHORIZED` | 인증 토큰이 없거나 유효하지 않은 경우 |
| 403 | `ERR_016` | `FORBIDDEN` | 관리자 권한이 없는 경우 |
| 404 | `ERR_010` | `EVENT NOT FOUND` | 이벤트를 찾을 수 없는 경우 |