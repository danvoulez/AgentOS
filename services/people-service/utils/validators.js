// services/people-service/utils/validators.js
export function validateEmail(email) {
  const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return re.test(String(email).toLowerCase());
}

export function validateRFID(tag) {
  return typeof tag === 'string' && tag.length >= 10;
}
