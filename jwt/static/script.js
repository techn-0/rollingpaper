$(document).ready(function() {
    $('#loginForm').submit(function(event) {
        event.preventDefault();
        $.ajax({
            type: 'POST',
            url: '/login',
            data: $(this).serialize(),
            success: function(response) {
                window.location.href = '/users';
            },
            error: function(response) {
                alert(response.responseJSON.message);
            }
        });
    });

    $('#signupForm').submit(function(event) {
        event.preventDefault();
        let formData = new FormData(this);  // 폼 데이터를 FormData 객체로 생성
    
        $.ajax({
            type: 'POST',
            url: '/signup',
            data: formData,
            processData: false,  // FormData 객체의 데이터를 문자열로 변환하지 않도록 설정
            contentType: false,  // FormData 객체의 Content-Type을 자동으로 설정하도록 설정
            success: function(response) {
                alert('회원가입 성공');
                window.location.href = '/login';
            },
            error: function(response) {
                alert(response.responseJSON.message);  // JSON 응답에서 메시지 추출
            }
        });
    });
});
