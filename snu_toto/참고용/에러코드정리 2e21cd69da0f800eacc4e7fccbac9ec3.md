# 에러코드정리

상태: 진행중

| **상태 코드** | **에러 코드** | **에러 메시지 (ERROR_MSG)** | **상황 설명** |
| --- | --- | --- | --- |
| 400 | `ERR_001` | MISSING REQUIRED FIELDS | 필수 요청 필드가 누락됨 |
| 400 | `ERR_002` | INVALID FIELD FORMAT | 필드 형식이 올바르지 않음 (이메일 형식 등) |
| 400 | `ERR_003` | BAD AUTHORIZATION HEADER | Authorization 헤더 형식이 잘못됨 |
| 401 | `ERR_004` | UNAUTHENTICATED | Authorization 헤더가 없음 |
| 401 | `ERR_005` | INVALID TOKEN | 유효하지 않거나 만료된 토큰 |
| 409 | `ERR_006` | EMAIL ALREADY EXISTS | 회원가입 시 이미 존재하는 이메일 |
| 409 | `ERR_007` | NICKNAME ALREADY EXISTS | 회원가입 시 이미 존재하는 닉네임 |
| 409 | `ERR_008` | EVENT OPTION CONFLICT | **같은 이벤트 내 옵션명이 중복될 경우** |
| 404 | `ERR_009` | EVENT NOT FOUND | **이벤트를 찾을 수 없는 경우** |
| 403 | `ERR_010` | ONLY SNU EMAIL ALLOWED | 이메일이 @snu.ac.kr 도메인이 아닌 경우 |
| 400 | `ERR_011` | EMAIL ALREADY VERIFIED | 이미 인증이 완료된 이메일 |
| 400 | `ERR_012` | INVALID VERIFICATION CODE | 이메일 인증 코드가 틀린 경우, 이메일 인증 시간이 초과된 경우 (5분 경과) |
| 500 | `ERR_013` | FAILED TO SEND EMAIL | 인증 메일 전송 실패 |
| 401 | `ERR_014` | INVALID CREDENTIALS | 이메일이 없거나 비밀번호가 틀린 경우 (보안상 통합) |
| 403 | `ERR_015` | EMAIL VERIFICATION REQUIRED | 계정은 있으나 아직 SNU 메일 인증을 안 한 사용자가 로그인 시도 |
| 400 | `ERR_016` | PASSWORD IS REQUIRED FOR LOCAL SIGNUP | 로컬 회원가입에서 password가 누락됨 |
| 400 | `ERR_017` | SOCIAL ID IS REQUIRED FOR SOCIAL SIGNUP | 소셜 회원가입에서 소셜 ID가 누락됨 |
| 409 | `ERR_018` | SOCIAL ID ALREADY EXISTS | 이미 가입된 소셜 ID |
| 400 | `ERR_019` | GOOGLE AUTH FAILED | 구글 서버와의 통신 중 오류 발생 (인가 코드 만료 등) |
| 400 | `ERR_020` | INVALID CALLBACK REQUEST | 필수 쿼리 파라미터(code)가 누락된 경우 |
| 429 | `ERR_021` | TOO MANY REQUESTS | 인증 메일 재발송 간격(1분) 미달 |
| 500 | `ERR_022` | FAILED TO SEND EMAIL | 인증 메일 전송 실패 |
| 400 | `ERR_023` | INVALID END DATE | 종료시각이 현재시각보다 이전인 경우 |
| 400 | `ERR_024` | INSUFFICIENT/TOO MANY OPTIONS | 옵션의 개수가 2개 미만 또는 10개 초과일 때 |
| 400 | `ERR_025` | INVALID OPTION NAME | 옵션 이름이 50자를 초과하거나 공백으로만 이루어진 옵션 이름 |
| 400 | `ERR_026` | INVALID OPTION ORDER | 옵션의 순서가 음수이거나 정수가 아닐 때 |
| 400 | `ERR_027` | INVALID IMAGE URL | 이미지 URL이 유효한 형식이 아닐 때 |
| 409 | `ERR_028` | DUPLICATE OPTION NAME | 한 이벤트 내에 동일한 이름의 옵션이 존재할 때 |
| 400 | `ERR_029` | INVALID STATUS TRANSITION | 잘못된 상태 전이 |
| 403 | `ERR_030` | NOT ADMIN | 관리자가 아닌 유저가 요청 |
| 400 | `ERR_031` | NEED WINNER ID | 상태변경시 승리 옵션 ID가 필요 |
| 400 | `ERR_032` | ALREADY CLOSED | 이미 종료 시각이 지난 이벤트를 오픈하려고 할 때 |
|  |  |  |  |