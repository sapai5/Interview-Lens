# Interview Lens

## Inspiration
As students looking for jobs and internships, we've had a lot of trouble figuring out how to pass interviews. The problem with the soft skills required for interviews are that you typically don't have instant feedback like you get with hard skills. When you're programming, you have an LSP, linters, and more that can tell you how many errors there are, what style guidelines you're breaking, and so on. You can't really tell, in the same way, whether your communication is error-free. So, as engineers, we naturally wanted to build a way to quantify this problem and generate real-time insights to solve it.

## What it does
Interview Lens is a dashboard that analyzes your camera in real-time, providing immediate feedback on your communication style, body language, and overall presentation. Our project uses computer vision and speech-to-text to track key metrics such as:

- Speech clarity and pace
- Filler word frequency
- Eye contact and facial expressions

## How we built it
We created Interview Lens using a stack of modern technologies:

- Frontend: Streamlit for UI framework, matplotlib for graphs
- Backend: AWS Rekognition for face data labeling, AWS Transcribe for speech to text
 
The most crucial component was building a real-time analysis pipeline that could process video and audio streams without introducing noticeable lag. We implemented a multi-threaded architecture that handles different analysis tasks in parallel, ensuring smooth performance even during extended interview sessions.

## Challenges we ran into
1. Real-time Processing: Balancing the accuracy of our AI models with the need for instant feedback required significant optimization. We eventually implemented a sliding window approach that analyzes 1-second chunks of video while maintaining smooth performance.

2. Privacy Concerns: Handling sensitive interview data required careful consideration. We implemented local processing where possible and ensured all server-bound data is securely transmitted.

## Accomplishments that we're proud of
- Quickly learned and developed with machine learning concepts like computer vision and speech to text
- Created a portable and intuitive UI with Streamlit

## What we learned
- The importance of UX and optimizing ML pipelines for real-time feedback systems
- How to handle sensitive user data responsibly

## What's next for Interview Lens
- Migrate project to a browser extension for increased integration with the user's workspace and potential use for during interviews
- Implement personalized AI models that learn from individual speaking styles and adapt feedback across different contexts
- Create practice rooms for mock interviews and peer feedback
- Develop an analytics dashboard for tracking long-term progress and communication patterns
