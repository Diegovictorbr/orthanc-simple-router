# Simple Router
A demonstration of an architecture containing multiple containerized Orthanc instances dedicated to a specific end. 

In this project, [Orthanc's routing functionality](https://github.com/amirkogithub/orthanc/blob/master/Resources/Samples/Python/HighPerformanceAutoRouting.py) is leveraged by using Docker Compose to define multiple writers.

In this simplified architecture, there are three containers:

- Router - An Orthanc container that forwards study instances based on its **modality** attribute.
- Generic writer - The writer container that stores all modalities in the filesystem
- X-ray writer - The specialized writer container that stores CR/DX studies in the filesystem